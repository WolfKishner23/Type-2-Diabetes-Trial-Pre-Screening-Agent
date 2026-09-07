"""Rank trials by clinical criterion fit; recruiting kept as separate field (no blended score)."""

from __future__ import annotations

from datetime import datetime, timezone

from models.criterion_state import CriterionState
from models.evaluation import CriterionEvaluation, PreScreenReport, RankedTrialMatch, TrialEvaluation
from models.patient import Patient
from models.trial import Trial

STATE_SCORE = {
    CriterionState.SUPPORTED: 2,
    CriterionState.UNKNOWN: 0,
    CriterionState.REQUIRES_CLINICAL_REVIEW: -1,
    CriterionState.CONFLICTING_EVIDENCE: -2,
    CriterionState.NOT_SUPPORTED: -3,
}

CLINICAL_CRITERIA = {"age", "hba1c", "current_diabetes_medications", "egfr"}


def _clinical_fit_score(criteria: list[CriterionEvaluation]) -> int:
    total = 0
    for c in criteria:
        if c.criterion not in CLINICAL_CRITERIA:
            continue
        total += STATE_SCORE.get(c.state, 0)
    return total


def _recruiting_label(trial: Trial) -> tuple[str, str]:
    status = trial.overall_status
    if status in ("RECRUITING", "ENROLLING_BY_INVITATION"):
        return status, "Trial is actively recruiting per frozen ClinicalTrials.gov snapshot."
    return status, "Trial is not actively recruiting in the frozen snapshot."


def _clinical_summary(criteria: list[CriterionEvaluation], out_of_scope: bool) -> str:
    parts: list[str] = []
    for c in criteria:
        if c.criterion in CLINICAL_CRITERIA:
            parts.append(f"{c.criterion}={c.state.value}")
    if out_of_scope:
        parts.append("additional_eligibility=REQUIRES_CLINICAL_REVIEW")
    return "; ".join(parts) if parts else "No clinical criteria evaluated."


def _collect_evidence_ids(evaluation: TrialEvaluation) -> list[str]:
    ids: list[str] = []
    for c in evaluation.criterion_results:
        ids.extend(c.evidence_ids)
    return sorted(set(ids))


_REVIEW_STATES = {
    CriterionState.UNKNOWN,
    CriterionState.REQUIRES_CLINICAL_REVIEW,
    CriterionState.CONFLICTING_EVIDENCE,
}


def _human_review_status(evaluation: TrialEvaluation) -> str:
    if evaluation.out_of_scope_requires_review:
        return "REQUIRED"
    for c in evaluation.criterion_results:
        if c.state in _REVIEW_STATES:
            return "REQUIRED"
    return "NOT_REQUIRED"


def _unanswered_questions(evaluation: TrialEvaluation) -> list[str]:
    questions: list[str] = []
    for c in evaluation.criterion_results:
        if c.state == CriterionState.UNKNOWN:
            req = c.trial_requirement
            if len(req) > 200:
                req = req[:200] + "…"
            questions.append(
                f"Does the patient meet the {c.criterion} requirement? "
                f"Trial expects: {req}"
            )
        elif c.state == CriterionState.REQUIRES_CLINICAL_REVIEW:
            reason = c.reason
            if len(reason) > 200:
                reason = reason[:200] + "…"
            questions.append(
                f"Clinical review needed for {c.criterion}: {reason}"
            )
        elif c.state == CriterionState.CONFLICTING_EVIDENCE:
            reason = c.reason
            if len(reason) > 200:
                reason = reason[:200] + "…"
            questions.append(
                f"Conflicting evidence for {c.criterion}: {reason}"
            )
    if evaluation.out_of_scope_requires_review and evaluation.out_of_scope_note:
        note = evaluation.out_of_scope_note
        if len(note) > 200:
            note = note[:200] + "…"
        questions.append(
            f"Out-of-scope eligibility clause requires review: {note}"
        )
    return questions


def rank_evaluations(
    patient: Patient,
    trial_by_id: dict[str, Trial],
    evaluations: list[TrialEvaluation],
    *,
    max_results: int = 3,
) -> list[RankedTrialMatch]:
    candidate_matches: list[tuple[int, int, int, TrialEvaluation]] = []
    for idx, ev in enumerate(evaluations):
        has_not_supported = any(c.state == CriterionState.NOT_SUPPORTED for c in ev.criterion_results)
        if has_not_supported:
            continue
            
        score = _clinical_fit_score(ev.criterion_results)
        if ev.out_of_scope_requires_review:
            score -= 1
        ambiguity_count = sum(1 for c in ev.criterion_results if c.state in _REVIEW_STATES)
        candidate_matches.append((score, ambiguity_count, idx, ev))

    candidate_matches.sort(key=lambda t: (-t[0], t[1], t[2]))
    matches: list[RankedTrialMatch] = []
    for rank, (score, _, _, ev) in enumerate(candidate_matches[:max_results], start=1):
        trial = trial_by_id[ev.nct_id]
        recruiting_status, recruiting_eligibility = _recruiting_label(trial)
        matches.append(
            RankedTrialMatch(
                rank=rank,
                nct_id=ev.nct_id,
                brief_title=ev.brief_title,
                recruiting_status=recruiting_status,
                recruiting_eligibility=recruiting_eligibility,
                clinical_fit_summary=_clinical_summary(ev.criterion_results, ev.out_of_scope_requires_review),
                clinical_fit_score=score,
                human_review_status=_human_review_status(ev),
                unanswered_questions=_unanswered_questions(ev),
                criterion_results=[c.to_report_dict() for c in ev.criterion_results],
                evidence_trace=_collect_evidence_ids(ev),
            )
        )
    return matches


def report_node(state: dict) -> dict:
    patient: Patient = state["patient"]
    trials: list[Trial] = state["all_trials"]
    evaluations: list[TrialEvaluation] = state.get("trial_evaluations") or []
    trial_by_id = {t.nct_id: t for t in trials}
    matches = rank_evaluations(patient, trial_by_id, evaluations, max_results=3)
    report = PreScreenReport(
        patient_id=patient.patient_id,
        patient_as_of_date=patient.as_of_date,
        generated_at=datetime.now(timezone.utc).isoformat(),
        disclaimer=(
            "Pre-screening aid only — not a clinical eligibility determination. "
            "All matches require qualified human review."
        ),
        trials_evaluated_count=len(evaluations),
        shortlisted_after_filter_count=len(state.get("shortlisted_trial_ids") or []),
        matches=matches,
    )
    return {"report": report}
