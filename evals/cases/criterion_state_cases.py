"""Expected criterion states for deterministic (USE_LLM=0) evaluations."""

CASES = [
    {
        "id": "crit_001",
        "patient_id": "P-2715",
        "nct_id": "NCT07057518",
        "criterion": "age",
        "expected_state": "SUPPORTED",
    },
    {
        "id": "crit_002",
        "patient_id": "P-1842",
        "nct_id": "NCT04536480",
        "criterion": "age",
        "expected_state": "NOT_SUPPORTED",
    },
    {
        "id": "crit_003",
        "patient_id": "P-2715",
        "nct_id": "NCT07057518",
        "criterion": "trial_recruiting_status",
        "expected_state": "SUPPORTED",
    },
    {
        "id": "crit_004",
        "patient_id": "P-1842",
        "nct_id": "NCT03301792",
        "criterion": "trial_recruiting_status",
        "expected_state": "NOT_SUPPORTED",
    },
    {
        "id": "crit_005",
        "patient_id": "P-1842",
        "nct_id": "NCT07011147",
        "criterion": "egfr",
        "expected_state": "REQUIRES_CLINICAL_REVIEW",
    },
    {
        "id": "crit_006",
        "patient_id": "P-1842",
        "nct_id": "NCT07011147",
        "criterion": "hba1c",
        "expected_state": "REQUIRES_CLINICAL_REVIEW",
    },
]
