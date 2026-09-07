# Sample run — patient P03 (`P-2715`, Cameron Rivera)

Command:

```bash
python src/main.py --patient_id P03 --output output/sample_patient_03_report.json
```

## Summary

- **As-of date:** 2026-07-01  
- **Age / gender:** 42 / female  
- **Latest labs (record):** HbA1c 8.6% (2026-05-23), eGFR 105 mL/min/1.73m²  
- **Active medication:** Empagliflozin 10 MG Oral Tablet  

After deterministic filters (recruiting + age), the graph evaluated each shortlisted trial against five criteria and ranked up to three matches by **clinical fit score**, keeping **recruiting status** as a separate column in the JSON report.

## Output

Full structured JSON is committed at `output/sample_patient_03_report.json`. Each match includes:

- `recruiting_status` / `recruiting_eligibility` (operational enrollment signal)
- `clinical_fit_score` / `clinical_fit_summary` (age, HbA1c, meds, eGFR only)
- `human_review_status` (REQUIRED/NOT_REQUIRED based on criterion evaluations)
- `unanswered_questions` (list of plain-text questions for UNKNOWN or REVIEW states)
- Per-criterion objects with `state`, `reason`, and `evidence_ids` (with appended lab/medication timestamps, e.g., `@2026-05-23`) pointing back to patient `source_id` values or `trial:{nct_id}:...` keys

## Reviewer notes

This run uses **Google Gemini** for LLM-assisted parsing of complex eligibility prose, cycling through keys if rate limits are hit. The system falls back to rule-based parsing if the LLM fails or is disabled (`USE_LLM=0`).

**Not a clinical decision** — intended pre-screening aid for human review.
