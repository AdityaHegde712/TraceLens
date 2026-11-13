# Evaluation, Reporting, and Deliverables

## Required Final Project Components

### 1. In-Class Presentation

The student must present the project in class, covering:
- Use case and target users.
- System design.
- Data sources and tools.
- Models or configurations compared.
- Evaluation results.
- Safety and robustness findings.
- System limitations and possible future improvements.
- Key takeaways.

### 2. Project Artifacts

Submitted artifacts must allow full inspection and evaluation by the instructor or ISA:
- Code or notebook.
- Data, documents, or database files (when shareable).
- Links to external data sources or APIs (when applicable).
- Prompt templates or system instructions.
- Test query set.
- Evaluation results.
- Safety, security, or robustness test results.
- Setup or run instructions.
- A short README/report.
- Slides, if required.
- Link to the demo recording.

### 3. Demo Recording

Must show the assistant working and include:
- Brief overview of the use case.
- Walkthrough of the system.
- At least a few representative queries.
- Explanation of major design choices.
- Discussion of at least one limitation or failure case.

## Evaluation and Trace Contract

The evaluation system must provide:

- **Query Coverage:** At least 20 realistic queries spanning common questions, data/tool-dependent questions, ambiguous requests, edge cases, and queries the assistant may fail.
- **Safety Suite:** At least 5 safety, security, or robustness tests relevant to the use case.
- **Standard Benchmark Suite:** Executes selected operations consistently across models or configurations.
- **Structured Traces:** Per-query traces recording:
  - Input query.
  - Expected behavior or answer.
  - Assistant response.
  - Configuration used.
  - Retrieved context (when applicable).
  - Tool calls and sequence flow (when applicable).
  - Deterministic checks.
  - Outcome (pass/fail).
  - Evaluator notes and failure limitations.
- **Aggregate Comparison:** Tradeoffs between configurations must be clearly explainable.
- **Evidence Separation:** Separate evidence streams for automated checks, live/manual verification, and packaging readiness.
- **Human Authority:** While an LLM-based evaluator may assist with scoring, classification, and template drafting, deterministic checks, inspectable traces, and human review remain the authoritative source of truth.

## README/Report Contract

The short README/report must be functional and directly useful for grading. It must document:
1. What the assistant does.
2. Who the target users are.
3. How to run or access the assistant.
4. What data sources and tools are used.
5. Which models or configurations were compared.
6. How the assistant was evaluated.
7. What safety or robustness tests were conducted.
8. What limitations were identified.
9. What improvements could be made in the future.

