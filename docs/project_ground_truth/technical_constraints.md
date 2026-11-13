# Locked Project Constraints

These constraints are non-negotiable boundaries established for the project lifecycle. Any deviation requires explicit recording in the ground truth before implementation.

## Individual Ownership and Academic Integrity

- The project is individual work.
- Coding agents may implement code, generate drafts, run checks, and organize artifacts under user supervision.
- The user retains ownership of high-level system design, scope approval, design decisions, credentials, benchmark launches, human review, final submission, and release decisions.
- The user expects the project to be built end-to-end by coding agents where practical, with the user supervising rather than manually implementing components.

## Cost and Reproducibility

- **Hard Zero Monetary Cost:** Paid APIs, paid cloud resources, and hidden usage charges must not be required for implementation, benchmarking, demonstration, or grading.
- **Candidate Model Options:** Local 3B and 8B models served through Ollama, free OpenAI-compatible endpoints (e.g., opencode-zen, hermes agent free models), free OpenRouter models, or other free services (subject to later verification).
- **BYOK / Optional External Services:** May be considered later only if isolated from the required reproducible path and not undermining the zero-cost constraint. This is an optional QoL feature, not a core deliverable.
- The project must be understandable and runnable from documented setup instructions without private agent context.

## User Experience and Execution Surfaces

- **Dual Surface Requirement:** The first complete delivery must provide both a browser UI and a CLI.
- **Backend First:** Backend functionality must be confirmed first via CLI before the frontend is built.
- **Surface Roles:**
  - **Browser UI:** Primary demonstration and peer-testing surface.
  - **CLI:** Repeatable surface for benchmark execution, debugging, evaluation, and grading evidence.
- **Launch Workflow:** Initial priority is a reliable clone-and-run workflow using a standard launch command or run script.
- **Installation Wizard:** A user-friendly installation wizard (e.g., supporting Dockerized CLI or system CLI choices) is low priority and deferred until the core project is stable.

## Architecture, Swappability, and Debug Operation

- **Backend Abstraction:** Model backends must be replaceable through a stable interface rather than hard-coded throughout the application.
- **Configurable Variants:** The system should support configurable comparison variants (model and workflow differences) without requiring a rebuild for every benchmark condition.
- **Semi-Hot-Swappable Operation:** The preferred direction is semi-hot-swappable operation: the system remains running while configured models, retrieval resources, or modules can be refreshed or swapped via a controlled debug workflow.
- **Debug Contract:** A possible debug contract is a `DEBUG` environment setting exposing a UI Refresh action and a corresponding backend refresh operation (design preference, not yet an implementation commitment).
- **Environment & Secrets:** Secrets and local environment settings must never be committed; configurations must be represented safely via `.env.example` and documented instructions.
- **Staged Progression:** Comparison work begins with two configurations to establish a feasible end-to-end baseline. Expansion to additional models/configurations occurs only after the core workflow and evaluation are stable.

## Potential Comparison Dimensions

Candidate comparison dimensions include:
- Which model is used.
- Retrieval + web search versus no retrieval (including context-window-dependent or web-search-dependent behavior).
- Alternative tool workflows.

> [!NOTE]
> If the eventual use case involves a transaction, the project may use a clearly labeled stub that assumes a successful transaction and bypasses a real payment API. No real payment processing is required.

