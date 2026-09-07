import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import pytest

from nodes.filter_node import filter_trials, passes_age_filter, passes_recruiting_filter
from utils.data_loader import load_dataset, resolve_patient_id


@pytest.fixture(scope="module")
def bundle():
    return load_dataset()


def test_dataset_loads(bundle):
    assert len(bundle.patients) == 15
    assert len(bundle.trials) == 36


def test_resolve_patient_shorthand(bundle):
    assert resolve_patient_id("P03", bundle.patients) == "P-2715"


def test_age_open_upper_bound(bundle):
    patient = next(p for p in bundle.patients if p.patient_id == "P-2715")
    trial = next(t for t in bundle.trials if t.maximum_age_years is None and t.minimum_age_years == 18.0)
    assert passes_age_filter(patient, trial) is True


def test_recruiting_filter_excludes_closed(bundle):
    trial = next(t for t in bundle.trials if t.overall_status == "ACTIVE_NOT_RECRUITING")
    assert passes_recruiting_filter(trial) is False


def test_filter_produces_shortlist(bundle):
    patient = next(p for p in bundle.patients if p.patient_id == "P-2715")
    ids = filter_trials(patient, bundle.trials)
    assert len(ids) > 0
    assert len(ids) <= len(bundle.trials)
