from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Condition(BaseModel):
    source_id: str
    code: str | None = None
    display: str | None = None
    clinical_status: str | None = None
    onset_date: str | None = None


class Observation(BaseModel):
    source_id: str
    type: str
    value: float | None = None
    unit: str | None = None
    effective_date: str | None = None
    status: str | None = None


class Medication(BaseModel):
    source_id: str
    name: str
    status: str
    start_date: str | None = None
    end_date: str | None = None


class PatientDemographics(BaseModel):
    patient_id: str
    age_at_reference_date: int | None = None
    birth_date: str | None = None
    administrative_gender: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class RecordQuality(BaseModel):
    missing_expected_domains: list[str] = Field(default_factory=list)
    source_note: str | None = None


class PregnancyStatus(BaseModel):
    source_id: str | None = None
    value: str | None = None
    effective_date: str | None = None


class Patient(BaseModel):
    schema_version: str | None = None
    patient_id: str
    as_of_date: str
    demographics: PatientDemographics
    conditions: list[Condition] = Field(default_factory=list)
    observations: list[Observation] = Field(default_factory=list)
    medications: list[Medication] = Field(default_factory=list)
    pregnancy_status: PregnancyStatus | None = None
    record_quality: RecordQuality | None = None

    @property
    def age(self) -> int | None:
        return self.demographics.age_at_reference_date

    def latest_observation(self, obs_type: str) -> Observation | None:
        matches = [o for o in self.observations if o.type == obs_type and o.value is not None]
        if not matches:
            return None
        return sorted(matches, key=lambda o: o.effective_date or "", reverse=True)[0]

    def active_medications(self) -> list[Medication]:
        return [m for m in self.medications if m.status.lower() == "active"]

    def model_dump_evidence(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
