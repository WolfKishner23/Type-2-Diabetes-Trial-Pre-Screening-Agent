import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from nodes.retrieve_node import build_evidence_bundle
from utils.data_loader import load_dataset


def test_retrieve_includes_evidence_ids():
    bundle = load_dataset()
    patient = bundle.patients[2]
    trial = next(t for t in bundle.trials if t.nct_id == "NCT07057518")
    pack = build_evidence_bundle(patient, trial)
    ps = pack["patient_snippet"]
    assert ps.get("age") == patient.age
    assert ps.get("hba1c_evidence_id") is not None
    ts = pack["trial_snippet"]
    assert ts["eligibility_source_id"] == f"trial:{trial.nct_id}:eligibility_text"
