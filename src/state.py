from __future__ import annotations

from typing import Any, TypedDict

from models.evaluation import CriterionEvaluation, PreScreenReport, TrialEvaluation
from models.patient import Patient
from models.trial import Trial


class PatientEvidenceSnippet(TypedDict, total=False):
    patient_id: str
    as_of_date: str
    age: int | None
    age_evidence_id: str | None
    gender: str | None
    gender_evidence_id: str | None
    latest_hba1c: float | None
    hba1c_evidence_id: str | None
    hba1c_effective_date: str | None
    all_hba1c: list[dict[str, Any]]
    latest_egfr: float | None
    egfr_evidence_id: str | None
    egfr_effective_date: str | None
    active_medications: list[dict[str, Any]]
    record_quality: dict[str, Any] | None


class TrialEvidenceSnippet(TypedDict, total=False):
    nct_id: str
    overall_status: str
    status_evidence_id: str
    minimum_age_years: float | None
    maximum_age_years: float | None
    age_requirement_text: str
    sex: str | None
    eligibility_excerpt: str
    eligibility_source_id: str
    hba1c_related_excerpt: str
    egfr_related_excerpt: str
    medication_related_excerpt: str


class TrialEvidenceBundle(TypedDict):
    nct_id: str
    trial: Trial
    patient_snippet: PatientEvidenceSnippet
    trial_snippet: TrialEvidenceSnippet


class AgentState(TypedDict, total=False):
    patient_id: str
    patient: Patient
    all_trials: list[Trial]
    shortlisted_trial_ids: list[str]
    evidence_bundles: list[TrialEvidenceBundle]
    trial_evaluations: list[TrialEvaluation]
    report: PreScreenReport
    error: str | None
