# Priorities, Deferred Decisions, and Non-Goals

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

> [!IMPORTANT]
> Deferred decisions must always be evaluated against locked constraints, specifically zero monetary cost, reproducibility, individual ownership, feasibility, and evidence quality.

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

