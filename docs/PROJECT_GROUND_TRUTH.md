# NLP Virtual Assistant Project Ground Truth

## Authority and Change Control

This document is the central router and authoritative index for the project's ground truth. All planning, implementation, evaluation, documentation, presentations, and demo deliverables must strictly satisfy the locked requirements and constraints detailed across the component documents below.

The files in `docs/deprecated/` are preserved historical inputs from the course assignment and the initial context-gathering process. They are retained for traceability but are not authoritative if they conflict with these documents.

Later project documents may refine decisions marked **deferred**. They must not silently weaken, remove, or contradict a locked requirement. Any intentional modification to a locked requirement must be recorded in this document suite before implementation proceeds.

---

## Central Documentation Index

The ground truth is organized into modular specifications under [`docs/project_ground_truth/`](project_ground_truth/):

| Area | Component File | Description & Scope |
| :--- | :--- | :--- |
| **Course & Scope** | [`course_and_scope.md`](project_ground_truth/course_and_scope.md) | Course context (CMPE-259), individual academic ownership, learning goals, and overarching scope definition. |
| **Proposal** | [`proposal_requirements.md`](project_ground_truth/proposal_requirements.md) | Required proposal contents, submission details, Complete criteria, and Incomplete criteria. |
| **Core Specification** | [`complete_specification.md`](project_ground_truth/complete_specification.md) | Baseline requirements for a **Complete** project across use case, assistant workflow, external tool integration, evaluation, peer testing, and artifacts. |
| **Advanced Rubric** | [`advanced_criteria.md`](project_ground_truth/advanced_criteria.md) | The target criteria for an **Advanced** grade (mandatory Tool Integration & Evaluation + at least 2 other focus areas). |
| **Architecture & Constraints** | [`technical_constraints.md`](project_ground_truth/technical_constraints.md) | Locked boundaries: **hard zero monetary cost**, dual execution surfaces (CLI first, browser UI), replaceable model backends, and debug capabilities. |
| **Evaluation & Deliverables** | [`evaluation_and_deliverables.md`](project_ground_truth/evaluation_and_deliverables.md) | Requirements for test query suites, safety tests, benchmark execution traces, human review, final presentations, and demo recordings. |
| **Roadmap & Non-Goals** | [`roadmap_and_deferred.md`](project_ground_truth/roadmap_and_deferred.md) | Active execution priorities, explicit list of deferred design choices, and anti-pattern non-goals. |

---

## Quality Tier Summary

- **Advanced (Target):** Meets all Complete requirements and demonstrates strong, artifact-backed evidence in tool/data integration (mandatory), systematic evaluation (mandatory), and at least two other designated focus areas.
- **Complete (Minimum Acceptable):** All core deliverables submitted, functional LLM assistant with external tool use, comparison of ≥2 configurations, ≥20 test queries, ≥5 safety/robustness tests, and peer evaluation.
- **Incomplete:** Any missing core artifact or non-evaluable requirement. Revised submission required.

---

## Historical References

Historical baseline documents are cataloged under `docs/deprecated/`:
- [`Project_Proposal_Requirements.md`](deprecated/Project_Proposal_Requirements.md)
- [`Project_Starter_Page.md`](deprecated/Project_Starter_Page.md)
- [`user_input.md`](deprecated/user_input.md)
