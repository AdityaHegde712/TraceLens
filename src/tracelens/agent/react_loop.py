"""Bounded ReAct agent orchestration loop for incident triage.

Enforces finite-state safety invariants including read-only mutation guards,
loop repetition detection, bounded step budgets, and dual-polarity evidence grounding.
"""

import json
import logging
import re
from collections import Counter
from enum import Enum
from typing import Any

from pydantic import ValidationError

from tracelens.agent.llm_backend import LLMBackend, MockLLMBackend
from tracelens.agent.tools import (
    BaseDiagnosticTool,
    ConfigLookupTool,
    LogSearchTool,
    MetricQueryTool,
    RunbookRetrieveTool,
    TraceInspectTool,
)
from tracelens.grounding.verifier import GroundingVerifier
from tracelens.models.triage import Hypothesis, TriageReport
from tracelens.telemetry.reader import IncidentBundle

DANGEROUS_MUTATION_PATTERN = re.compile(
    r"(?i)\b(restart|reboot|delete|drop|kill|terminate|truncate|update|write|modify|exec|bash|sh|rm\s+-rf)\b"
)

logger = logging.getLogger(__name__)


class AgentState(str, Enum):
    """FSM states of the Bounded ReAct Agent."""

    INIT = "INIT"
    THINKING = "THINKING"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    EVALUATING_GROUNDING = "EVALUATING_GROUNDING"
    TERMINATED = "TERMINATED"
    ABSTAINED = "ABSTAINED"
    MUTATION_REFUSED = "MUTATION_REFUSED"


SYSTEM_PROMPT = """You are TraceLens, an evidence-grounded incident triage assistant.
You operate in strict read-only mode to diagnose root causes of microservice and RAG pipeline failures.

Available tools:
- log_search: args: {service?: str, level?: str, query?: str, limit?: int}
- trace_inspect: args: {trace_id?: str}
- metric_query: args: {metric_name?: str, pod?: str}
- config_lookup: args: {service?: str}
- runbook_retrieve: args: {query?: str}
- finish: args: {hypotheses: list[Hypothesis]}

Output format: Return valid JSON with keys:
{
  "thought": "Your diagnostic reasoning",
  "action": "tool_name or finish",
  "args": { ... },
  "hypotheses": [ ... ] (when action is finish)
}

Few-shot diagnostic example:
User Symptom: "High P99 latency and intermittent 504 timeouts on /query"
Step 1:
{
  "thought": "First, inspect error logs from the retrieval service to identify exceptions.",
  "action": "log_search",
  "args": {"service": "retrieval-service", "level": "ERROR"}
}
Observation: [{"timestamp": "...", "service": "retrieval-service", "message": "Upstream timeout to vector-db"}]

Step 2:
{
  "thought": "Log shows vector-db timeout. Inspect distributed trace to identify the bottleneck span.",
  "action": "trace_inspect",
  "args": {"trace_id": "tr-001"}
}
Observation: {"critical_path": [{"span_id": "sp-2", "name": "milvus_search", "duration_ms": 4200.0}], "bottlenecks": [{"span_id": "sp-2", "self_time_ms": 4150.0}]}

Step 3:
{
  "thought": "Trace bottleneck confirms milvus_search took 4.15s. Ground diagnosis with evidence citations.",
  "action": "finish",
  "hypotheses": [
    {
      "hypothesis_id": "H1",
      "title": "Vector Store Search Bottleneck",
      "description": "Milvus vector query latency degraded causing gateway 504 timeouts.",
      "confidence": 0.95,
      "evidence_links": [
        {
          "evidence_id": "sp-2",
          "source_type": "trace",
          "polarity": "support",
          "description": "Span milvus_search latency 4150ms bottleneck",
          "relevance_score": 0.95
        }
      ]
    }
  ]
}
"""


class BoundedReActAgent:
    """Bounded ReAct agent conducting structured read-only triage."""

    def __init__(
        self,
        bundle: IncidentBundle,
        llm: LLMBackend | None = None,
        max_steps: int = 5,
        verifier: GroundingVerifier | None = None,
    ) -> None:
        """Initialize the agent with telemetry bundle and safety parameters."""
        self.bundle = bundle
        self.llm = llm or MockLLMBackend()
        self.max_steps = max_steps
        self.verifier = verifier or GroundingVerifier(min_evidence_weight=0.5)

        self.state = AgentState.INIT
        self.step_count = 0
        self.action_history: list[tuple[str, str]] = []
        self.scratchpad: list[dict[str, Any]] = []

        # Tool registry
        self.tools: dict[str, BaseDiagnosticTool] = {
            "log_search": LogSearchTool(bundle),
            "trace_inspect": TraceInspectTool(bundle),
            "metric_query": MetricQueryTool(bundle),
            "config_lookup": ConfigLookupTool(bundle),
            "runbook_retrieve": RunbookRetrieveTool(bundle),
        }

    def run(self, symptom: str | None = None) -> TriageReport:
        """Execute the bounded ReAct loop until diagnostic termination or abstention.

        Args:
            symptom: Incident alert or reported symptom.

        Returns:
            Structured TriageReport grounded with telemetry evidence.
        """
        incident_id = self.bundle.manifest.incident_id
        active_symptom = symptom or self.bundle.manifest.symptom

        # 1. Refusal Guard
        if DANGEROUS_MUTATION_PATTERN.search(active_symptom):
            self.state = AgentState.MUTATION_REFUSED
            return TriageReport(
                incident_id=incident_id,
                reported_symptom=active_symptom,
                status="abstained",
                primary_root_cause=None,
                confidence=0.0,
                abstention_reason=(
                    "Mutating operation refused: TraceLens operates in strict read-only diagnostic mode."
                ),
            )

        self.state = AgentState.THINKING
        candidate_hypotheses: list[Hypothesis] = []

        while self.step_count < self.max_steps:
            prompt = self._build_prompt(active_symptom)
            llm_output = self.llm.generate(prompt=prompt, system_prompt=SYSTEM_PROMPT)

            parsed = self._parse_llm_output(llm_output)
            action = str(parsed.get("action", "")).strip().lower()
            args = parsed.get("args", {})
            if not isinstance(args, dict):
                args = {}

            # Check if LLM finished
            if action == "finish" or "hypotheses" in parsed:
                candidate_hypotheses = self._extract_hypotheses(parsed)
                break

            if action not in self.tools:
                # If tool unknown or missing, break to synthesis
                break

            # 2. Loop Detection Guard
            call_sig = (action, json.dumps(args, sort_keys=True))
            self.action_history.append(call_sig)
            counts = Counter(self.action_history)
            if counts[call_sig] > 2:
                # Break infinite loop
                break

            # 3. Tool Execution
            self.state = AgentState.TOOL_EXECUTION
            tool = self.tools[action]
            try:
                observation = tool.execute(**args)
            except (ValueError, KeyError, TypeError, RuntimeError) as e:
                logger.warning("Tool execution error for action %s: %s", action, e)
                observation = {"error": str(e)}

            self.scratchpad.append({
                "step": self.step_count + 1,
                "thought": parsed.get("thought", ""),
                "action": action,
                "args": args,
                "observation": observation,
            })
            self.step_count += 1
            self.state = AgentState.THINKING

        # 4. Evaluating Grounding and Final Synthesis
        self.state = AgentState.EVALUATING_GROUNDING
        assessment = self.verifier.verify(candidate_hypotheses)

        if assessment.status == "diagnosed":
            self.state = AgentState.TERMINATED
        elif assessment.status == "abstained":
            self.state = AgentState.ABSTAINED
        else:
            self.state = AgentState.TERMINATED

        return TriageReport(
            incident_id=incident_id,
            reported_symptom=active_symptom,
            status=assessment.status,
            primary_root_cause=assessment.primary_root_cause,
            confidence=assessment.confidence,
            hypotheses=assessment.hypotheses,
            abstention_reason=assessment.abstention_reason,
        )

    def _build_prompt(self, symptom: str) -> str:
        """Construct context scratchpad prompt for LLM."""
        return (
            f"Incident: {self.bundle.manifest.title}\n"
            f"Reported Symptom: {symptom}\n"
            f"Services Involved: {', '.join(self.bundle.manifest.services_involved)}\n\n"
            f"Scratchpad History:\n{json.dumps(self.scratchpad, indent=2)}\n\n"
            f"Current step {self.step_count + 1} of {self.max_steps}. What is your next thought and action?"
        )

    def _parse_llm_output(self, raw: str) -> dict[str, Any]:
        """Safely extract structured JSON payload from LLM response.

        Handles markdown code fences (```json ... ```), embedded JSON objects,
        and provides resilient fallback if JSON is incomplete or malformed.
        """
        cleaned = raw.strip()

        # 1. Direct JSON parse
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return self._normalize_parsed_action(parsed)
        except json.JSONDecodeError:
            pass

        # 2. Markdown fenced block extraction: ```json ... ``` or ``` ... ```
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL | re.IGNORECASE)
        if fence_match:
            try:
                parsed = json.loads(fence_match.group(1))
                if isinstance(parsed, dict):
                    return self._normalize_parsed_action(parsed)
            except json.JSONDecodeError:
                pass

        # 3. Outer brace matching for embedded JSON object
        outer_match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if outer_match:
            try:
                parsed = json.loads(outer_match.group(1))
                if isinstance(parsed, dict):
                    return self._normalize_parsed_action(parsed)
            except json.JSONDecodeError:
                pass

        # 4. Fallback: extract thoughts safely and default to finish
        return {"thought": cleaned, "action": "finish", "args": {}, "hypotheses": []}

    def _normalize_parsed_action(self, parsed: dict[str, Any]) -> dict[str, Any]:
        """Normalize action string by stripping whitespace and lowercasing."""
        if "action" in parsed and isinstance(parsed["action"], str):
            parsed["action"] = parsed["action"].strip().lower()
        return parsed

    def _extract_hypotheses(self, parsed: dict[str, Any]) -> list[Hypothesis]:
        """Extract and validate Hypothesis objects from LLM finish action."""
        hyp_list = parsed.get("hypotheses", [])
        extracted: list[Hypothesis] = []
        for h_dict in hyp_list:
            try:
                extracted.append(Hypothesis.model_validate(h_dict))
            except (ValidationError, TypeError, ValueError) as exc:
                logger.debug("Skipping invalid hypothesis dictionary %s: %s", h_dict, exc)
                continue
        return extracted
