from __future__ import annotations

from pydantic import BaseModel, Field


class TrialLocation(BaseModel):
    facility: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class TrialSource(BaseModel):
    url: str | None = None
    retrieved_on: str | None = None
    record_version_date: str | None = None


class Trial(BaseModel):
    schema_version: str | None = None
    nct_id: str
    brief_title: str | None = None
    official_title: str | None = None
    study_type: str | None = None
    overall_status: str
    conditions: list[str] = Field(default_factory=list)
    minimum_age: str | None = None
    maximum_age: str | None = None
    minimum_age_years: float | None = None
    maximum_age_years: float | None = None
    sex: str | None = None
    healthy_volunteers: bool | None = None
    eligibility_text: str
    locations: list[TrialLocation] = Field(default_factory=list)
    source: TrialSource | None = None

    @property
    def trial_id(self) -> str:
        return self.nct_id
