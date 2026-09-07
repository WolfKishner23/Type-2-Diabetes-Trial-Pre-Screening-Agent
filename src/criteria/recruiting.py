"""Trial recruiting status criterion (frozen snapshot)."""

from __future__ import annotations

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from state import TrialEvidenceBundle

SYSTEM_PROMPT = """Evaluate whether the trial's overall_status indicates active recruitment.
SUPPORTED only for RECRUITING or ENROLLING_BY_INVITATION.
NOT_SUPPORTED for completed/closed/not yet recruiting statuses when clearly stated.
Do not guess; use UNKNOWN only if status missing."""


def evaluate(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    ts = bundle["trial_snippet"]
    status = ts.get("overall_status")
    evidence = [ts["status_evidence_id"]]
    trial_requirement = "Trial must be actively recruiting (RECRUITING or ENROLLING_BY_INVITATION) in the frozen snapshot."

    if not status:
        return CriterionEvaluation(
            criterion="trial_recruiting_status",
            state=CriterionState.UNKNOWN,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason="Trial overall_status is missing from the supplied record.",
            evidence_ids=evidence,
        )

    if status in ("RECRUITING", "ENROLLING_BY_INVITATION"):
        return CriterionEvaluation(
            criterion="trial_recruiting_status",
            state=CriterionState.SUPPORTED,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason=f"Trial status is {status}, which indicates active recruitment in the snapshot.",
            evidence_ids=evidence,
        )

    return CriterionEvaluation(
        criterion="trial_recruiting_status",
        state=CriterionState.NOT_SUPPORTED,
        patient_value=None,
        trial_requirement=trial_requirement,
        reason=f"Trial status is {status}, which is not active recruitment in the snapshot.",
        evidence_ids=evidence,
    )
