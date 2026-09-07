from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from models.patient import Patient
from models.trial import Trial


class DatasetBundle(BaseModel):
    dataset_meta: dict[str, Any]
    assignment_scope: dict[str, Any]
    data_dictionary: dict[str, Any]
    patients: list[Patient]
    trials: list[Trial]


def default_dataset_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "Type2-Diabetes-Trial-Agent-Dataset.json"


def load_dataset(path: Path | None = None) -> DatasetBundle:
    path = path or default_dataset_path()
    raw = json.loads(path.read_text(encoding="utf-8"))
    try:
        bundle = DatasetBundle(
            dataset_meta=raw.get("dataset", {}),
            assignment_scope=raw.get("assignment_scope", {}),
            data_dictionary=raw.get("data_dictionary", {}),
            patients=[Patient.model_validate(p) for p in raw["patients"]],
            trials=[Trial.model_validate(t) for t in raw["trials"]],
        )
    except (KeyError, ValidationError) as exc:
        raise ValueError(f"Dataset validation failed for {path}: {exc}") from exc
    return bundle


def resolve_patient_id(requested: str, patients: list[Patient]) -> str:
    """Accept P-2715 or shorthand P03 (1-based index in file order)."""
    requested = requested.strip()
    ids = [p.patient_id for p in patients]
    if requested in ids:
        return requested
    upper = requested.upper()
    if upper.startswith("P") and upper[1:].isdigit():
        idx = int(upper[1:]) - 1
        if 0 <= idx < len(ids):
            return ids[idx]
    raise ValueError(
        f"Unknown patient_id {requested!r}. Use a dataset id (e.g. P-2715) or index shorthand (e.g. P03)."
    )


def get_patient(bundle: DatasetBundle, patient_id: str) -> Patient:
    resolved = resolve_patient_id(patient_id, bundle.patients)
    for p in bundle.patients:
        if p.patient_id == resolved:
            return p
    raise ValueError(f"Patient {resolved} not found")
