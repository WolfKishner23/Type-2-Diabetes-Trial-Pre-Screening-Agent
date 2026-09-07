"""Deterministic pre-filters: recruiting status, then age range."""

from __future__ import annotations

from models.patient import Patient
from models.trial import Trial

RECRUITING_PASS_STATUSES = frozenset({"RECRUITING", "ENROLLING_BY_INVITATION"})


def passes_recruiting_filter(trial: Trial) -> bool:
    return trial.overall_status.upper() in RECRUITING_PASS_STATUSES


def passes_age_filter(patient: Patient, trial: Trial) -> bool:
    age = patient.age
    if age is None:
        return False
    min_y = trial.minimum_age_years
    max_y = trial.maximum_age_years
    if min_y is not None and age < min_y:
        return False
    if max_y is not None and age > max_y:
        return False
    return True


def filter_trials(patient: Patient, trials: list[Trial]) -> list[str]:
    shortlisted: list[str] = []
    for trial in trials:
        if not passes_recruiting_filter(trial):
            continue
        if not passes_age_filter(patient, trial):
            continue
        shortlisted.append(trial.nct_id)
    return shortlisted


def filter_node(state: dict) -> dict:
    patient: Patient = state["patient"]
    trials: list[Trial] = state["all_trials"]
    ids = filter_trials(patient, trials)
    return {"shortlisted_trial_ids": ids}
