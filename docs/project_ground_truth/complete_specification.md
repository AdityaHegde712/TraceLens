# Complete Project Specification

The final project is **Complete** only when every requirement below is satisfied.

## 1. Specific Use Case
The assistant is designed for a clearly defined use case and target user. The use case is narrow enough that assistant behavior can be meaningfully evaluated.

## 2. Working LLM-Based Assistant
The project includes a functional virtual assistant that uses a large language model to respond to realistic user queries. It does not need to be a polished product, but it must be functional enough to demonstrate the core workflow.

## 3. External Data or Tool Use
At least one meaningful external data source or tool is central to the use case, not a superficial add-on. Acceptable categories include:
- Structured dataset or database.
- Collection of documents.
- Retrieval-augmented generation system.
- API.
- Web-based source.
- Search or scraping component.
- Tool-calling workflow.
- Case-specific skill definitions (such as coding-agent skills generalized to the selected use case; optional consideration, not a required specification).

## 4. Model or Configuration Comparison
At least two LLMs or meaningfully different system configurations are compared. Possible comparison dimensions include:
- Smaller versus larger model.
- Different prompting strategies.
- Retrieval versus no retrieval.
- Different chunking or retrieval settings.
- Different tool-use workflows.
- Different temperature or decoding settings.
- Different grounding or citation strategies.

The comparison must explain tradeoffs rather than merely state which option “seemed better.”

## 5. Test Query Set
The test set contains at least 20 realistic user queries relevant to the use case. It must include a mixture of:
- Common user questions.
- Questions requiring data or tool use.
- Ambiguous or underspecified questions.
- Edge cases.
- Questions the assistant may not be able to answer reliably.

## 6. Evaluation Evidence
Evaluation evidence shows how the assistant performed on the test query set. Each evaluated case must record:
- Query asked.
- Expected behavior or expected answer.
- Assistant response.
- Whether the response was successful.
- Errors, limitations, or failure-mode notes.

The evaluation does not need to be perfect, but it must be systematic enough to support a meaningful conclusion.

## 7. Safety, Security, and Robustness Testing
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

## 8. Peer/User Testing
At least two classmates test the assistant. The final artifacts must summarize:
- Who tested the assistant.
- What types of queries they tried.
- What worked well.
- What failed or confused users.
- What was changed, or what would be changed, based on feedback.

## 9. Presentation and Demo
The in-class presentation and demo recording are completed and cover the required topics:
- **Presentation:** Explains use case, target users, system design, data sources/tools, models compared, evaluation results, safety/robustness findings, limitations, and key takeaways.
- **Demo Recording:** Shows the assistant working, provides use case overview, system walkthrough, representative queries, architecture choices, and at least one limitation or failure case.

## 10. Inspectable Artifacts
The final submission contains enough implementation, source, configuration, evaluation, setup, and explanation material for an instructor or ISA to reproduce or inspect the core project.

