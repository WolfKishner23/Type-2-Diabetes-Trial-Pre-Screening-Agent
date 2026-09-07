# AI usage disclosure

## Tools used and their roles

**Antigravity IDE (Gemini-based)** — primary implementation tool.
Used for writing and debugging all source code: nodes, criteria modules, models, state schema, eval harness, and tests. Also used to catch and fix a silent correctness bug in the exclusion-clause parsing logic (see below).

**Claude (Anthropic)** — architecture review and scope-checking.
Used to review design proposals before implementing them, specifically to evaluate whether a 5-node graph (one LLM call per criterion) was within assignment scope. Rejected that suggestion based on the "four-node" requirement and cost/explainability concerns. Also used to sense-check the `REQUIRES_CLINICAL_REVIEW` fallback strategy and identify tasks 6–9 in the final review pass.

**Kimi / other AI tools** — early exploration only.
Used during initial architecture brainstorming (data model layout, retrieval strategy options). No code from this phase was carried forward directly.

---

## Accepted suggestion

**Structured criterion objects via Pydantic + optional LangChain `with_structured_output`.**
Recommended by Antigravity: one shared `CriterionEvaluation` model for all five modules so report JSON, tests, and LLM outputs stay aligned. Accepted because it enforces the assignment schema (`state`, `evidence_ids`, etc.) and reduces parse bugs.

**Verification:** pytest on graph output; manual check that every criterion dict includes the five required keys; `evals/run_evals.py` criterion state cases.

## Rejected suggestion

**Splitting each criterion into its own LangGraph node (5+ LLM rounds per trial).**
Proposed by Claude during an architecture review of a Kimi-generated design. Rejected per assignment architecture: exactly four nodes, one evaluate node looping criteria modules. Keeps the graph explainable and avoids redundant model calls. This was an explicit example of cross-examining an AI suggestion rather than accepting it — the rejected design was reviewed against the assignment spec before any code was written.

**Verification:** `src/graph.py` lists four nodes only; `evaluate_node.py` imports a single evaluator list.

---

## Final behavior verification

- `USE_LLM=0` runs end-to-end with rule-based modules (CI / eval reproducibility).
- With `GEMINI_API_KEYS`, hba1c/medications/egfr may call the model but fall back to rules on failure.
- Verified exclusion-clause parsing logic via manual verification on trial `NCT07011147` (where the system now correctly routes to `REQUIRES_CLINICAL_REVIEW` instead of misinterpreting the exclusion threshold) and added two new evaluation test cases in the test suite to guard against future regressions. This bug was caught and fixed using Antigravity after the first full eval run — it would have silently misclassified borderline eGFR patients.
- No conversation logs stored in-repo; this file is the disclosure summary only.
