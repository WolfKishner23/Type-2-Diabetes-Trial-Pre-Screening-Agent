import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from nodes.report_node import rank_evaluations
from utils.data_loader import load_dataset


def test_report_separates_recruiting_from_clinical_score():
    bundle = load_dataset()
    patient = bundle.patients[0]
    trial = bundle.trials[0]
    ev = __import__("models.evaluation", fromlist=["TrialEvaluation"]).TrialEvaluation(
        nct_id=trial.nct_id,
        brief_title=trial.brief_title,
        criterion_results=[
            CriterionEvaluation(
                criterion="age",
                state=CriterionState.SUPPORTED,
                patient_value=60,
                trial_requirement="18-50",
                reason="ok",
                evidence_ids=["patient:P-1842:demographics"],
            )
        ],
    )
    matches = rank_evaluations(patient, {trial.nct_id: trial}, [ev], max_results=1)
    assert matches[0].recruiting_status == trial.overall_status
    assert "recruiting" not in matches[0].clinical_fit_summary.lower() or "trial_recruiting" not in matches[0].clinical_fit_summary
