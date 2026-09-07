import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from criteria.states import CriterionState
from graph import build_graph
from utils.data_loader import load_dataset


def test_full_graph_rule_mode(monkeypatch):
    monkeypatch.setenv("USE_LLM", "0")
    bundle = load_dataset()
    patient = next(p for p in bundle.patients if p.patient_id == "P-2715")
    app = build_graph()
    out = app.invoke({"patient_id": patient.patient_id, "patient": patient, "all_trials": bundle.trials})
    report = out["report"]
    assert report.patient_id == "P-2715"
    assert len(report.matches) <= 3
    for match in report.matches:
        assert match.recruiting_status
        assert match.clinical_fit_score is not None
        for cr in match.criterion_results:
            assert cr["state"] in {s.value for s in CriterionState}
            assert cr["evidence_ids"]
