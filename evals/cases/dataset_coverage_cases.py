"""Dataset coverage: every patient id resolves; trial count stable."""

CASES = [
    {"id": "cov_001", "expected_patients": 15, "expected_trials": 36},
    {"id": "cov_002", "patient_index": 1, "expected_id": "P-1842"},
    {"id": "cov_003", "patient_index": 15, "expected_id": "P-9157"},
]
