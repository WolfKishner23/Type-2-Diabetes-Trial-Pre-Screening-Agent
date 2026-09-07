"""Eval cases: retrieval field correctness."""

CASES = [
    {
        "id": "ret_001",
        "patient_id": "P-2715",
        "nct_id": "NCT07057518",
        "expect_hba1c_evidence": True,
        "expect_eligibility_source": "trial:NCT07057518:eligibility_text",
    },
    {
        "id": "ret_002",
        "patient_id": "P-1842",
        "nct_id": "NCT07005986",
        "expect_hba1c_evidence": True,
        "expect_eligibility_source": "trial:NCT07005986:eligibility_text",
    },
    {
        "id": "ret_003",
        "patient_id": "P-9157",
        "nct_id": "NCT07047248",
        "expect_hba1c_evidence": True,
        "expect_eligibility_source": "trial:NCT07047248:eligibility_text",
    },
]
