"""Age criterion: explicit evaluation for trials that passed the age pre-filter."""

from __future__ import annotations

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from state import TrialEvidenceBundle

SYSTEM_PROMPT = """You evaluate whether a patient's age meets a trial's age eligibility.
Use ONLY supplied patient and trial fields. If patient age is missing, state must be UNKNOWN.
Never infer age. Respond using the structured evaluation object."""


def _rule_based(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    ps = bundle["patient_snippet"]
    ts = bundle["trial_snippet"]
    age = ps.get("age")
    evidence: list[str] = []
    if ps.get("age_evidence_id"):
        evidence.append(ps["age_evidence_id"])
    evidence.append(ts["status_evidence_id"])

    req_parts: list[str] = []
    min_y = ts.get("minimum_age_years")
    max_y = ts.get("maximum_age_years")
    if min_y is not None:
        req_parts.append(f"minimum {min_y} years")
    else:
        req_parts.append("no minimum age in record")
    if max_y is not None:
        req_parts.append(f"maximum {max_y} years")
    else:
        req_parts.append("no maximum age in record (open upper bound)")
    trial_requirement = "; ".join(req_parts)

    if age is None:
        return CriterionEvaluation(
            criterion="age",
            state=CriterionState.UNKNOWN,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason="Patient age is not established in the supplied demographics record.",
            evidence_ids=sorted(set(evidence)),
        )

    if min_y is not None and age < min_y:
        return CriterionEvaluation(
            criterion="age",
            state=CriterionState.NOT_SUPPORTED,
            patient_value=age,
            trial_requirement=trial_requirement,
            reason=f"Patient age {age} is below the trial minimum of {min_y} years.",
            evidence_ids=sorted(set(evidence)),
        )
    if max_y is not None and age > max_y:
        return CriterionEvaluation(
            criterion="age",
            state=CriterionState.NOT_SUPPORTED,
            patient_value=age,
            trial_requirement=trial_requirement,
            reason=f"Patient age {age} exceeds the trial maximum of {max_y} years.",
            evidence_ids=sorted(set(evidence)),
        )

    return CriterionEvaluation(
        criterion="age",
        state=CriterionState.SUPPORTED,
        patient_value=age,
        trial_requirement=trial_requirement,
        reason=f"Patient age {age} falls within the trial age range ({trial_requirement}).",
        evidence_ids=evidence,
    )


def evaluate(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    from utils.llm_client import llm_enabled

    if not llm_enabled():
        return _rule_based(bundle)
    # LLM path reserved for edge cases; deterministic comparison is authoritative for numeric age.
    return _rule_based(bundle)
