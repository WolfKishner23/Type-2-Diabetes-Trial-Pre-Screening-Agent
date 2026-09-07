import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from utils.data_loader import load_dataset, resolve_patient_id


def test_all_patients_resolve():
    bundle = load_dataset()
    for p in bundle.patients:
        assert resolve_patient_id(p.patient_id, bundle.patients) == p.patient_id
