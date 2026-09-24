# My Thoughts, Preferences, and Choices for the Project.

**NOTE**: These preferences are loose and running thoughts the user had when reviewing the project information myself. If something is infeasable, pushback and suggest an alternative. If something is too ambitious or a bad design choice, pushback, suggest an alternative. These preferences are not set in stone, engage with the user in a discussion and interactive interview to refine and figure stuff out. This is part of a context-gathering turn, so the interview questions should be of the same nature.

## User thoughts:

Project - I want the entire project to be purely LLM-completed, end-end. So my coding agents, antigravity and codex, would build it end-end. I should only be in charge of supervision and high-level system design.

Let's have, say, 20 queries for testing, simple, advanced, and security query types (more info in project desc file). Models I can benchmark: Local 8B and 3B params (so the small param category, served via ollama server), opencode-big-pickle via openai compatible url and api key, hy3 via openai compatible url and api key, some from openrouter (big param models), bring-your-own-api-key, demo-intended gemini ig. Plug-n-play design for model backend use.

There are comparison criterias, so when designing the system we should create that with a semi-hot-swappable plug-n-play architecture as well (system stays on, loaded resources/modules can be refreshed or swapped in and out on demand in 'debug mode' via a config update or something when the environment variable $DEBUG is true in the .env. The $DEBUG being true will enable a "Refresh" button in the UI and a refresh contract for the user to try it, and during benchmarking the backend contract would exist anyway and the LLM doing the benchmark can take care of it.)

For the comparative study itself, I'm thinking we add comparative swappable utilities for:

- which model to use
- Retrieval+web-search system vs no-retrieval context-window-dependent and web-search-dependent system
- Tool workflows (may be strong, but needs to be well-thought-out)
  And we compare any 4 LLMs out of our options (Let's do the local 3B and 8B models, we choose 2 other models that are huge, maybe one ~70B and one frontier size model via openrouter, maybe from this page: https://openrouter.ai/models?variant=free. I don't want to pay for it for sure.

For the comparison report generation we can build a test suite that runs a standard set of chosen benchmark operations, and then an LLM (likely codex or antigravity agent) assesses the outputs, tool calls, sequence flows, and fills a standard templated report, so different tests don't need to be manual. The template for the report and comparison study is in the project description.

If project is transaction-involved, let's have a stub that assumes the transaction was successful and bypasses the actual payment api, we don't need for it to be paid.

We're shooting for 'Advanced'.

For installation, as a late-stage-development let's include a user-friendly cli-based or UI based wizard that lets the user choose running method (dockerized cli path that would ask the user to download docker if unavailable, system cli path, others can be explored). This is a low-priority task. Standard front-end launch via git clone and a run script should be the deliverance priority, we can wrap it neatly later for installation.
