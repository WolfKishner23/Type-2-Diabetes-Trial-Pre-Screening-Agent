from __future__ import annotations

from typing import Callable

from criteria import age, egfr, hba1c, medications, recruiting
from models.evaluation import TrialEvaluation
from state import TrialEvidenceBundle

CRITERION_EVALUATORS: list[tuple[str, Callable[[TrialEvidenceBundle], object]]] = [
    ("age", age.evaluate),
    ("hba1c", hba1c.evaluate),
    ("current_diabetes_medications", medications.evaluate),
    ("egfr", egfr.evaluate),
    ("trial_recruiting_status", recruiting.evaluate),
]

OUT_OF_SCOPE_KEYWORDS = [
    "pregnant",
    "pregnancy",
    "lactating",
    "bmi",
    "body mass",
    "schizophrenia",
    "cancer",
    "stroke",
    "myocardial",
    "english",
    "turkish",
    "consent",
    "cognitive",
    "psychiatric",
]


def trial_has_out_of_scope_requirements(bundle: TrialEvidenceBundle) -> tuple[bool, str | None]:
    text = (bundle["trial"].eligibility_text or "").lower()
    hits = [kw for kw in OUT_OF_SCOPE_KEYWORDS if kw in text]
    if not hits:
        return False, None
    note = (
        "Trial eligibility text includes requirements outside the five automated criteria "
        f"({', '.join(sorted(set(hits))[:8])}). Human clinical review is required before enrollment decisions."
    )
    return True, note


def evaluate_node(state: dict) -> dict:
    bundles: list[TrialEvidenceBundle] = state.get("evidence_bundles") or []
    evaluations: list[TrialEvaluation] = []
    for bundle in bundles:
        results = [eval_fn(bundle) for _, eval_fn in CRITERION_EVALUATORS]
        out_of_scope, note = trial_has_out_of_scope_requirements(bundle)
        evaluations.append(
            TrialEvaluation(
                nct_id=bundle["nct_id"],
                brief_title=bundle["trial"].brief_title,
                criterion_results=results,
                out_of_scope_requires_review=out_of_scope,
                out_of_scope_note=note,
            )
        )
    return {"trial_evaluations": evaluations}
