"""Bounded ReAct agent orchestration loop for incident triage.

Enforces finite-state safety invariants including read-only mutation guards,
loop repetition detection, bounded step budgets, and dual-polarity evidence grounding.
"""

from collections import Counter
from enum import Enum
import json
import re
from typing import Any

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
            action = parsed.get("action", "")
            args = parsed.get("args", {})

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
            except Exception as e:
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
        """Safely extract structured JSON payload from LLM response."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Try regex search for embedded JSON block
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        return {"thought": raw, "action": "finish"}

    def _extract_hypotheses(self, parsed: dict[str, Any]) -> list[Hypothesis]:
        """Extract and validate Hypothesis objects from LLM finish action."""
        hyp_list = parsed.get("hypotheses", [])
        extracted: list[Hypothesis] = []
        for h_dict in hyp_list:
            try:
                extracted.append(Hypothesis.model_validate(h_dict))
            except Exception:
                continue
        return extracted
