# Advanced Target Quality Criteria

The project must satisfy every **Complete** requirement before Advanced quality is claimed. To earn **Advanced**, it must show strong evidence in at least **four** of the nine areas below, and the first two areas are mandatory:

1. **Tool/Data Integration** — mandatory.
2. **Evaluation** — mandatory.
3. **System Design**.
4. **Model/Configuration Comparison**.
5. **Grounding**.
6. **Robustness/Security**.
7. **Usability**.
8. **Technical Quality**.
9. **Reflection**.

> [!IMPORTANT]
> “Strong evidence” means the area is demonstrated with project-specific artifacts, observed results, and an explanation of tradeoffs or limitations. A planned feature or unverified claim does not count.

---

### 1. Tool/Data Integration (Mandatory)

Counts as strong when:
- The external data source or tool is central to the assistant’s primary task.
- The integration is functional in the demo and benchmark path.
- The project documents the source, access method, assumptions, and failure behavior.
- Evaluation includes queries that require the data or tool.
- Results show whether the assistant used the external information correctly rather than merely mentioning that it exists.

### 2. Evaluation (Mandatory)

Counts as strong when:
- The query set is realistic, varied, and use-case-specific.
- Expected behavior and success criteria are defined before judging outputs.
- Results are captured systematically across comparison configurations.
- Aggregate results support meaningful conclusions about quality and tradeoffs.
- Failures, uncertainty, limitations, and evaluator disagreement are reported rather than hidden.

### 3. System Design

Counts as strong when:
- The architecture is appropriate for the use case and project scale.
- Major design choices are documented with reasons and tradeoffs.
- The interaction flow between user, LLM, retrieval, tools, and evidence capture is understandable.
- Failure modes have explicit handling or clear limitations.
- The design avoids unnecessary complexity while leaving the comparison path reproducible.

### 4. Model/Configuration Comparison

Counts as strong when:
- At least two models or configurations are evaluated on the same relevant workload.
- The comparison controls or documents important variables such as prompts, query set, temperature, retrieval settings, and tool availability.
- Results include more than a single subjective preference.
- The report explains quality, latency, cost, capability, reliability, or other relevant tradeoffs.
- The selected comparison is feasible under the zero-cost project path.

### 5. Grounding

Counts as strong when:
- Responses that require external knowledge are supported by retrieved or tool-derived evidence.
- The assistant distinguishes supported information from uncertainty or missing information.
- Citations, source references, excerpts, or equivalent evidence are inspectable when appropriate.
- The evaluation tests unsupported claims, stale or conflicting information, and missing evidence.
- The project discusses grounding failures and does not claim that retrieval alone guarantees truth.

### 6. Robustness/Security

Counts as strong when:
- Tests cover realistic misuse, adversarial inputs, missing data, ambiguity, conflicting information, and tool or retrieval failure where relevant.
- Direct and indirect prompt-injection risks are considered when external content or tools are used.
- The project records actual behavior, not only intended safeguards.
- Unsafe, out-of-scope, or unsupported requests receive bounded behavior.
- Findings lead to specific mitigations, limitations, or future work.

### 7. Usability

Counts as strong when:
- A realistic user can understand how to start, ask questions, and interpret responses.
- The browser UI provides a coherent demonstration and peer-testing experience.
- Errors, unavailable tools, missing information, and unsupported requests are communicated clearly.
- Peer testing produces concrete observations about confusion, usefulness, and workflow friction.
- The project documents changes or proposed changes based on user feedback.

### 8. Technical Quality

Counts as strong when:
- The code, notebooks, prompts, data references, and evaluation artifacts are organized and understandable.
- Setup and run instructions are reproducible on the intended environment.
- Benchmark runs produce inspectable outputs and avoid silent failures.
- Configuration and model backends are replaceable without widespread code changes.
- Known limitations, dependency requirements, and operational assumptions are documented.

### 9. Reflection

Counts as strong when:
- The final report and presentation explain what worked and what failed.
- Limitations are specific and supported by observed evidence.
- Tradeoffs and unexpected findings are discussed honestly.
- Future improvements are connected to observed failure modes or unmet user needs.
- The project distinguishes completed capabilities from proposed future work.

