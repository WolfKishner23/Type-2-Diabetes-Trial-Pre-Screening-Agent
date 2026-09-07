from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from models.criterion_state import CriterionState


class CriterionEvaluation(BaseModel):
    criterion: str
    state: CriterionState
    patient_value: Any = None
    trial_requirement: str
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)

    def to_report_dict(self) -> dict[str, Any]:
        return {
            "criterion": self.criterion,
            "state": self.state.value,
            "patient_value": self.patient_value,
            "trial_requirement": self.trial_requirement,
            "reason": self.reason,
            "evidence_ids": self.evidence_ids,
        }


class TrialEvaluation(BaseModel):
    nct_id: str
    brief_title: str | None = None
    criterion_results: list[CriterionEvaluation] = Field(default_factory=list)
    out_of_scope_requires_review: bool = False
    out_of_scope_note: str | None = None


class RankedTrialMatch(BaseModel):
    rank: int
    nct_id: str
    brief_title: str | None = None
    recruiting_status: str
    recruiting_eligibility: str
    clinical_fit_summary: str
    clinical_fit_score: int
    human_review_status: str = "NOT_REQUIRED"
    unanswered_questions: list[str] = Field(default_factory=list)
    criterion_results: list[dict[str, Any]] = Field(default_factory=list)
    evidence_trace: list[str] = Field(default_factory=list)


class PreScreenReport(BaseModel):
    patient_id: str
    patient_as_of_date: str
    generated_at: str
    disclaimer: str
    trials_evaluated_count: int
    shortlisted_after_filter_count: int
    matches: list[RankedTrialMatch] = Field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
