"""Field lookup retrieval for the five in-scope criteria (no vector DB)."""

from __future__ import annotations

import re

from models.patient import Patient
from models.trial import Trial
from state import PatientEvidenceSnippet, TrialEvidenceBundle, TrialEvidenceSnippet


def _extract_sentences_containing(text: str, keywords: list[str], max_chars: int = 1200) -> str:
    if not text:
        return ""
    pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
    chunks: list[str] = []
    for block in re.split(r"(?<=[.!?])\s+|\n+", text):
        if pattern.search(block):
            chunks.append(block.strip())
    joined = " ".join(chunks)
    if not joined:
        return text[:max_chars]
    return joined[:max_chars]


def build_patient_snippet(patient: Patient) -> PatientEvidenceSnippet:
    demo = patient.demographics
    latest_hba1c = patient.latest_observation("hba1c")
    latest_egfr = patient.latest_observation("egfr")
    all_hba1c = [
        {
            "source_id": (
                f"{o.source_id}@{o.effective_date}" if o.effective_date else o.source_id
            ),
            "value": o.value,
            "unit": o.unit,
            "effective_date": o.effective_date,
        }
        for o in patient.observations
        if o.type == "hba1c"
    ]
    active_meds = [
        {
            "source_id": (
                f"{m.source_id}@{m.start_date}" if m.start_date else m.source_id
            ),
            "name": m.name,
            "status": m.status,
            "start_date": m.start_date,
        }
        for m in patient.active_medications()
    ]
    return PatientEvidenceSnippet(
        patient_id=patient.patient_id,
        as_of_date=patient.as_of_date,
        age=patient.age,
        age_evidence_id=f"patient:{patient.patient_id}:demographics",
        gender=demo.administrative_gender,
        gender_evidence_id=f"patient:{patient.patient_id}:demographics",
        latest_hba1c=latest_hba1c.value if latest_hba1c else None,
        hba1c_evidence_id=(
            f"{latest_hba1c.source_id}@{latest_hba1c.effective_date}"
            if latest_hba1c and latest_hba1c.effective_date
            else (latest_hba1c.source_id if latest_hba1c else None)
        ),
        hba1c_effective_date=latest_hba1c.effective_date if latest_hba1c else None,
        all_hba1c=all_hba1c,
        latest_egfr=latest_egfr.value if latest_egfr else None,
        egfr_evidence_id=(
            f"{latest_egfr.source_id}@{latest_egfr.effective_date}"
            if latest_egfr and latest_egfr.effective_date
            else (latest_egfr.source_id if latest_egfr else None)
        ),
        egfr_effective_date=latest_egfr.effective_date if latest_egfr else None,
        active_medications=active_meds,
        record_quality=patient.record_quality.model_dump() if patient.record_quality else None,
    )


def build_trial_snippet(trial: Trial) -> TrialEvidenceSnippet:
    elig = trial.eligibility_text or ""
    return TrialEvidenceSnippet(
        nct_id=trial.nct_id,
        overall_status=trial.overall_status,
        status_evidence_id=f"trial:{trial.nct_id}:overall_status",
        minimum_age_years=trial.minimum_age_years,
        maximum_age_years=trial.maximum_age_years,
        age_requirement_text=f"min={trial.minimum_age or 'open'}, max={trial.maximum_age or 'open'}",
        sex=trial.sex,
        eligibility_excerpt=elig[:2000],
        eligibility_source_id=f"trial:{trial.nct_id}:eligibility_text",
        hba1c_related_excerpt=_extract_sentences_containing(
            elig, ["hba1c", "a1c", "hemoglobin", "glycated", "HbA1c"]
        ),
        egfr_related_excerpt=_extract_sentences_containing(
            elig, ["egfr", "gfr", "creatinine clearance", "renal", "kidney", "nephrop"]
        ),
        medication_related_excerpt=_extract_sentences_containing(
            elig,
            [
                "medication",
                "insulin",
                "metformin",
                "sglt",
                "glp",
                "sulfonylurea",
                "semaglutide",
                "empagliflozin",
                "drug",
                "therapy",
            ],
        ),
    )


def build_evidence_bundle(patient: Patient, trial: Trial) -> TrialEvidenceBundle:
    return TrialEvidenceBundle(
        nct_id=trial.nct_id,
        trial=trial,
        patient_snippet=build_patient_snippet(patient),
        trial_snippet=build_trial_snippet(trial),
    )


def retrieve_node(state: dict) -> dict:
    patient: Patient = state["patient"]
    trials: list[Trial] = state["all_trials"]
    shortlisted: set[str] = set(state.get("shortlisted_trial_ids") or [])
    trial_by_id = {t.nct_id: t for t in trials}
    bundles: list[TrialEvidenceBundle] = []
    for nct_id in shortlisted:
        trial = trial_by_id.get(nct_id)
        if trial is None:
            continue
        bundles.append(build_evidence_bundle(patient, trial))
    return {"evidence_bundles": bundles}
