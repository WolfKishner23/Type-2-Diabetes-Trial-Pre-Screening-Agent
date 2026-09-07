# Research notes — data dictionary and retrieval design

## Data dictionary (summary)

| Domain | Key fields | Evidence IDs |
|--------|------------|--------------|
| Patient | `patient_id`, `as_of_date`, `demographics.age_at_reference_date` | `source_id` on observations/meds/conditions; synthetic demographic key `patient:{id}:demographics` |
| Labs | `observations[]` with `type` in (`hba1c`, `egfr`, …) | `observation.source_id` |
| Meds | `medications[]` with `status` | `medication.source_id` |
| Trial | `nct_id`, `overall_status`, age years, `eligibility_text` | `trial:{nct_id}:overall_status`, `trial:{nct_id}:eligibility_text` |

Assignment scope (from dataset): five automated criteria — age, HbA1c, current diabetes medications, eGFR, trial recruiting status. All other eligibility themes → human `REQUIRES_CLINICAL_REVIEW`, not silent exclusion.

## Retrieval design (no embeddings)

**Approach:** structured field lookup plus lightweight text slicing.

For each `(patient, shortlisted trial)` pair, `retrieve_node` builds:

1. **Patient snippet** — latest HbA1c/eGFR by `effective_date`, all HbA1c rows (conflict detection), active medications, demographics age/gender, `record_quality.missing_expected_domains`.
2. **Trial snippet** — structured age bounds, `overall_status`, full eligibility text capped at 2k chars, and **criterion-targeted excerpts** produced by sentence-level keyword filters (HbA1c, renal, medication vocabulary).

**Rationale:** The assignment dataset is small, JSON-native, and criterion-scoped. Embeddings would add infrastructure without improving traceability — every retrieved fact maps directly to a JSON path or `source_id`. Excerpting keeps LLM prompts (when enabled) within context while preserving citeable trial text.

**Chunking:** Sentences/bullet lines matching criterion keywords; if none match, fall back to the eligibility header window. Not semantic chunking — intentional simplicity for audit.

**Separation:** Patient facts and trial facts never merged into a single blob; evaluate modules receive both sides explicitly.

## Age filter vs age criterion

- **Filter (1b):** hard drop if patient age outside `[minimum_age_years, maximum_age_years]` with open null bounds.
- **Criterion (evaluate):** re-states the same comparison with full `CriterionEvaluation` schema for survivors — satisfies “explicit evaluation” without contradicting filter results.

## Recruiting filter vs recruiting criterion

- **Filter (1a):** keeps only `RECRUITING` and `ENROLLING_BY_INVITATION` trials in the shortlist.
- **Criterion:** still emits structured recruiting evaluation for traceability and report fields (`recruiting_status` separate from clinical fit score).

## Human review status

Across the full dataset (15 patients × 36 trials), `human_review_status` evaluates to `REQUIRED` in 100% of cases — driven by (a) the strict no-guessing rule on `UNKNOWN` criteria and (b) nearly every trial containing at least one out-of-scope eligibility clause. This reflects the dataset's characteristics and the system's conservative design, not a logic error. `clinical_fit_score` and the specific criterion states remain the primary signal for prioritization.

## HbA1c vs eGFR Variance Checking (Design Decision)

`hba1c.py` checks for variance across multiple readings and flags `CONFLICTING_EVIDENCE` if found, reflecting that HbA1c changes slowly and high variance signals a data/assay issue. `egfr.py` intentionally uses only the most recent reading without a variance check, since eGFR is expected to fluctuate acutely for physiological reasons (hydration, acute illness, medication changes) — using the latest value is the safer clinical default for renal eligibility rather than averaging or deferring on normal fluctuation.
