# NLP Virtual Assistant Project Ground Truth

## Authority and Change Control

This document is the authoritative source of truth for the project. All future planning, implementation, evaluation, documentation, presentation, and demo work must satisfy the locked requirements and constraints below.

The files in `docs/deprecated/` are preserved historical inputs from the course assignment and the initial context-gathering process. They are retained for traceability but are not authoritative if they conflict with this document.

Later project documents may refine decisions currently marked **deferred**. They must not silently weaken, remove, or contradict a locked requirement. Any intentional change to a locked requirement must be explicitly recorded here before implementation proceeds.

## Project Identity and Course Context

- Course: FA26 CMPE-259 Section 01 - Natural Language Process.
- Project type: Individual LLM-based virtual assistant project.
- Proposal submission: PDF file upload, due Friday by 11:59 p.m. on the date configured for the assignment; the proposal is worth 1 point.
- Proposal source: [Canvas Assignment 7794691](https://sjsu.instructure.com/courses/1635001/assignments/7794691).
- Academic responsibility: Each student owns their own use case, implementation, evaluation, artifacts, presentation, and demo recording.
- Primary outcome: A working, inspectable, reproducible virtual assistant that combines an LLM with meaningful external information or tools.
- Target quality level: **Advanced**.
- Minimum acceptable quality level: **Complete**.

## Project Purpose and Learning Goals

The project must demonstrate that the student can:

1. Define a realistic LLM-based virtual assistant use case.
2. Design an assistant that uses external data or tools.
3. Implement a working prototype.
4. Compare models or system configurations.
5. Evaluate the assistant using realistic user queries.
6. Test the system for safety, security, robustness, and limitations.
7. Communicate technical design decisions clearly.
8. Reflect on what works, what fails, and what could be improved.

The assistant should help a realistic target user answer questions or complete tasks. It must be more specific than a broad general-purpose chatbot. For example, “a travel assistant” is too broad; an assistant that helps students compare study-abroad programs using budget, dates, and course requirements is specific enough to evaluate.

## Proposal Requirements

### Proposal purpose

The proposal must establish that the project is specific, feasible, and appropriate for the course. It must give the instructor or ISA enough information to judge feasibility before implementation. Proposals are submitted individually. Peer support groups are assigned after proposals are reviewed.

### Required proposal contents

The proposal must include:

1. Project title.
2. Specific use case.
3. Clearly defined target users or target user group.
4. What the assistant will help those users do.
5. Planned external data source or tool.
6. Planned LLMs or meaningfully different system configurations to compare.
7. At least 20 draft user queries.
8. Initial safety, security, or robustness concerns.
9. Expected technical or operational challenges.

### Proposal Complete criteria

A proposal is **Complete** when it:

- Defines a specific and realistic use case.
- Identifies a target user group.
- Includes a plausible plan for meaningful external data or tool use.
- Identifies at least two models or system configurations to compare.
- Includes at least 20 draft user queries.
- Identifies at least one likely challenge or risk.
- Provides enough detail for the instructor or ISA to determine feasibility.

### Proposal Incomplete criteria

A proposal is **Incomplete** when one or more of the following applies:

- The scope is too broad or vague.
- The project is not sufficiently focused on NLP or LLMs.
- The proposal does not include a data or tool plan.
- The proposal does not include a model or configuration comparison plan.
- The required query set is missing.
- There is not enough information to determine feasibility.

An Incomplete grade means a revised proposal is expected before the next project check-in.

## Required Final Project Components

### In-class presentation

The student must present the project in class. The presentation must explain:

- Use case and target users.
- System design.
- Data sources and tools.
- Models or configurations compared.
- Evaluation results.
- Safety and robustness findings.
- System limitations and possible future improvements.
- Key takeaways.

### Project artifacts

The submitted artifacts must be sufficient for the instructor or ISA to inspect and evaluate the project. They must include:

- Code or notebook.
- Data, documents, or database files when shareable.
- Links to external data sources or APIs when applicable.
- Prompt templates or system instructions.
- Test query set.
- Evaluation results.
- Safety, security, or robustness test results.
- Setup or run instructions.
- A short README/report.
- Slides, if required.
- Link to the demo recording.

The written report is not a separate grading category, but a short, functional README/report is required as part of the project artifacts.

### Demo recording

The demo recording must show the assistant working and include:

- Brief overview of the use case.
- Walkthrough of the system.
- At least a few representative queries.
- Explanation of major design choices.
- Discussion of at least one limitation or failure case.

## Project Status Labels

- **Advanced:** Meets all Complete requirements and demonstrates strong overall quality in the required Advanced areas.
- **Complete:** All required components are submitted or completed, and the core specifications are met.
- **Incomplete:** One or more required components is missing or cannot be evaluated.

## Complete Project Specification

The final project is **Complete** only when every requirement below is satisfied.

### 1. Specific use case

The assistant is designed for a clearly defined use case and target user. The use case is narrow enough that assistant behavior can be meaningfully evaluated.

### 2. Working LLM-based assistant

The project includes a functional virtual assistant that uses a large language model to respond to realistic user queries. It does not need to be a polished product, but it must be functional enough to demonstrate the core workflow.

### 3. External data or tool use

At least one meaningful external data source or tool is central to the use case, not a superficial add-on. Acceptable categories include:

- Structured dataset or database.
- Collection of documents.
- Retrieval-augmented generation system.
- API.
- Web-based source.
- Search or scraping component.
- Tool-calling workflow.
- Case-specific skill definitions, such as coding-agent skills generalized to the selected use case; optional consideration, not a required specification.

### 4. Model or configuration comparison

At least two LLMs or meaningfully different system configurations are compared. Possible comparison dimensions include:

- Smaller versus larger model.
- Different prompting strategies.
- Retrieval versus no retrieval.
- Different chunking or retrieval settings.
- Different tool-use workflows.
- Different temperature or decoding settings.
- Different grounding or citation strategies.

The comparison must explain tradeoffs rather than merely state which option “seemed better.”

### 5. Test query set

The test set contains at least 20 realistic user queries relevant to the use case. It must include a mixture of:

- Common user questions.
- Questions requiring data or tool use.
- Ambiguous or underspecified questions.
- Edge cases.
- Questions the assistant may not be able to answer reliably.

### 6. Evaluation evidence

Evaluation evidence shows how the assistant performed on the test query set. Each evaluated case must record:

- Query asked.
- Expected behavior or expected answer.
- Assistant response.
- Whether the response was successful.
- Errors, limitations, or failure-mode notes.

The evaluation does not need to be perfect, but it must be systematic enough to support a meaningful conclusion.

### 7. Safety, security, and robustness testing

At least 5 safety, security, or robustness tests are performed and documented. Relevant categories include:

- Direct prompt injection.
- Indirect prompt injection through retrieved or external content.
- Hallucinations or unsupported claims.
- Requests outside the assistant’s scope.
- Tool misuse.
- Data leakage.
- Unsafe or inappropriate user requests.
- Ambiguous queries.
- Conflicting information.
- Missing information.

The results must explain what happened and what the findings suggest about system limitations.

### 8. Peer/user testing

At least two classmates test the assistant. The final artifacts must summarize:

- Who tested the assistant.
- What types of queries they tried.
- What worked well.
- What failed or confused users.
- What was changed, or what would be changed, based on feedback.

### 9. Presentation and demo

The in-class presentation and demo recording are completed and cover the required topics above.

### 10. Inspectable artifacts

The final submission contains enough implementation, source, configuration, evaluation, setup, and explanation material for an instructor or ISA to reproduce or inspect the core project.

## Advanced Target Criteria

The project must satisfy every Complete requirement before Advanced quality is claimed. To earn Advanced, it must show strong evidence in at least **four** of the nine areas below, and the first two areas are mandatory:

1. Tool/data integration — mandatory.
2. Evaluation — mandatory.
3. System design.
4. Model/configuration comparison.
5. Grounding.
6. Robustness/security.
7. Usability.
8. Technical quality.
9. Reflection.

“Strong evidence” means the area is demonstrated with project-specific artifacts, observed results, and an explanation of tradeoffs or limitations. A planned feature or unverified claim does not count.

### 1. Tool/data integration — mandatory

Counts as strong when:

- The external data source or tool is central to the assistant’s primary task.
- The integration is functional in the demo and benchmark path.
- The project documents the source, access method, assumptions, and failure behavior.
- Evaluation includes queries that require the data or tool.
- Results show whether the assistant used the external information correctly rather than merely mentioning that it exists.

### 2. Evaluation — mandatory

Counts as strong when:

- The query set is realistic, varied, and use-case-specific.
- Expected behavior and success criteria are defined before judging outputs.
- Results are captured systematically across comparison configurations.
- Aggregate results support meaningful conclusions about quality and tradeoffs.
- Failures, uncertainty, limitations, and evaluator disagreement are reported rather than hidden.

### 3. System design

Counts as strong when:

- The architecture is appropriate for the use case and project scale.
- Major design choices are documented with reasons and tradeoffs.
- The interaction flow between user, LLM, retrieval, tools, and evidence capture is understandable.
- Failure modes have explicit handling or clear limitations.
- The design avoids unnecessary complexity while leaving the comparison path reproducible.

### 4. Model/configuration comparison

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

### 6. Robustness/security

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

### 8. Technical quality

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

## Locked Project Constraints

### Individual ownership and academic integrity

- The project is individual work.
- Agents may implement code, generate drafts, run checks, and organize artifacts under user supervision.
- The user retains ownership of high-level system design, scope approval, design decisions, credentials, benchmark launches, human review, final submission, and release decisions.
- The user expects the project to be built end-to-end by coding agents where practical, with the user supervising rather than manually implementing components.

### Cost and reproducibility

- The required project path is hard zero-monetary-cost.
- Paid APIs, paid cloud resources, and hidden usage charges must not be required for implementation, benchmarking, demonstration, or grading.
- Candidate model options may include local 3B and 8B models served through Ollama, free OpenAI-compatible endpoints like opencode-zen and hermes agent's free models, free OpenRouter models, or other free services, subject to later verification.
- BYOK or optional external services may be considered later only if they are isolated from the required reproducible path and do not undermine the zero-cost constraint. Not a core deliverable, just a QoL feature which can optionally be added later.
- The project must be understandable and runnable from documented setup instructions without private agent context.

### User experience and execution surfaces

- The first complete delivery must provide both a browser UI and a CLI. Backend functionality confirmed first via CLI, then the frontend is built. Backend comes first.
- The browser UI is the primary demonstration and peer-testing surface.
- The CLI is the repeatable surface for benchmark execution, debugging, evaluation, and grading evidence.
- The initial priority is a reliable clone-and-run workflow using a standard launch command or run script.
- A user-friendly installation wizard may later support choices such as a Dockerized CLI path or system CLI path, but it is low priority and deferred until the core project is stable.

### Architecture, swappability, and debug operation

- Model backends must be replaceable through a stable interface rather than hard-coded throughout the application.
- The system should support configurable comparison variants, including model and workflow differences, without requiring a rebuild for every benchmark condition.
- The preferred direction is semi-hot-swappable operation: the system remains running while configured models, retrieval resources, or modules can be refreshed or swapped through a controlled debug workflow.
- A possible debug contract is a `DEBUG` environment setting that exposes a UI Refresh action and a corresponding backend refresh operation. This is a design preference, not yet an implementation commitment.
- Environment-specific secrets and local settings must not be committed; any configuration contract must be represented safely through example configuration and documented setup instructions.
- Comparison work begins with two configurations to establish a feasible end-to-end baseline.
- Expansion to additional models or configurations is allowed only after the core workflow, evidence capture, and evaluation are stable.

### Potential comparison dimensions

The comparative study may eventually provide swappable utilities for:

- Which model is used.
- Retrieval plus web search versus no retrieval, including context-window-dependent or web-search-dependent behavior.
- Alternative tool workflows.

These are candidate comparison dimensions, not final decisions. Any selected tool workflow must be well-defined, feasible, and evaluated rather than added for novelty.

If the eventual use case involves a transaction, the project may use a clearly labeled stub that assumes a successful transaction and bypasses a real payment API. No real payment processing is required.

## Evaluation, Trace, and Report Contract

The evaluation system must include:

- At least 20 realistic queries spanning common questions, data/tool-dependent questions, ambiguous requests, edge cases, and questions the assistant may not answer reliably.
- At least 5 safety, security, or robustness tests selected from risks relevant to the final use case.
- A standard benchmark suite that runs selected operations consistently across models or configurations.
- Structured per-query traces containing the input, expected behavior or answer, assistant output, configuration used, retrieved context when applicable, tool calls and sequence flow when applicable, deterministic checks, outcome, evaluator notes, and limitations.
- Aggregate comparison results that make tradeoffs between models or configurations explainable.
- Separate evidence for automated checks, live/manual verification, and final packaging or release readiness.
- Human review of evaluation results and sampled traces.

An LLM-based evaluator may assess outputs, tool calls, sequence flows, and failure traces, then populate a standardized comparison-report template. The evaluator may assist with scoring, classification, error analysis, and report drafting, but it is not the sole authority for project conclusions. Deterministic checks, inspectable traces, and human review remain authoritative.

The location and aggregation of evaluation evidence must be clearly documented so the user can inspect, explain, and defend the results. Automated report generation must preserve links or identifiers back to the underlying evidence.

## README/Report Content Contract

The short README/report must be functional and useful for grading. It must explain:

- What the assistant does.
- Who the target users are.
- How to run or access the assistant.
- What data sources and tools are used.
- Which models or configurations were compared.
- How the assistant was evaluated.
- What safety or robustness tests were conducted.
- What limitations were identified.
- What improvements could be made in the future.

## Current Priorities

1. Establish and validate a specific, feasible use case.
2. Produce a proposal that satisfies all Complete proposal requirements.
3. Build a reliable end-to-end assistant with a browser UI and CLI.
4. Capture reproducible traces and evaluation evidence before expanding comparison breadth.
5. Complete the Advanced evidence areas, prioritizing tool/data integration and evaluation.
6. Add installation convenience features only after the core deliverable is stable.

## Deferred Decisions

The following decisions must be made in a later idea-selection and design phase:

- Specific use case and target users.
- External data source, document collection, database, API, retrieval system, or web-based source.
- Exact model providers, model names, local runtime, and free endpoint availability.
- Whether the eventual comparison includes two configurations only or expands toward four LLMs.
- Exact comparison configurations and benchmark matrix.
- Tool-calling workflow, retrieval workflow, web-search behavior, and grounding/citation behavior.
- Final query set and safety/robustness test cases.
- Browser UI technology and CLI command structure.
- Artifact formats and storage layout for traces and reports.
- Exact refresh contract and debug-mode implementation.
- Whether a transaction stub is relevant to the selected use case.
- Optional installation wizard design.

Deferred decisions must be evaluated against the locked constraints in this document, especially zero cost, reproducibility, individual ownership, feasibility, and evidence quality.

## Explicit Non-Goals

The project will not:

- Require paid services or paid infrastructure.
- Treat a broad general-purpose chatbot as a sufficiently specific use case.
- Add external data or tools merely as superficial integrations.
- Treat an LLM-generated report as a substitute for raw evidence and human review.
- Expand model or configuration breadth before the core end-to-end workflow is reliable.
- Prioritize an installation wizard over the working assistant, CLI benchmark path, or evaluation artifacts.
- Invent or lock a specific project idea before the dedicated idea-selection phase.
- Claim Advanced quality based only on planned features, unverified model availability, aggregate scores without traces, or unaudited evaluator output.

## Historical References

The original course requirements, starter page, and initial user notes are preserved under `docs/deprecated/`:

- [`Project_Proposal_Requirements.md`](deprecated/Project_Proposal_Requirements.md)
- [`Project_Starter_Page.md`](deprecated/Project_Starter_Page.md)
- [`user_input.md`](deprecated/user_input.md)

These files provide provenance for this ground-truth document. This document takes precedence over them for all subsequent project work.
