#!/usr/bin/env python3
"""Run assignment eval cases (USE_LLM=0 for reproducibility)."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

os.environ.setdefault("USE_LLM", "0")

from cases.agent_behavior_cases import CASES as AGENT_CASES
from cases.criterion_state_cases import CASES as CRIT_CASES
from cases.dataset_coverage_cases import CASES as COV_CASES
from cases.retrieval_cases import CASES as RET_CASES
from original_metric import evidence_traceability_completeness
from criteria import age, recruiting, egfr, hba1c
from graph import build_graph
from nodes.retrieve_node import build_evidence_bundle
from utils.data_loader import get_patient, load_dataset


def run() -> int:
    bundle = load_dataset()
    app = build_graph()
    failures: list[str] = []
    passed = 0

    for case in COV_CASES:
        if "expected_patients" in case:
            if len(bundle.patients) != case["expected_patients"]:
                failures.append(f"{case['id']}: patient count (expected {case['expected_patients']}, got {len(bundle.patients)})")
            else:
                passed += 1
        if "expected_trials" in case:
            if len(bundle.trials) != case["expected_trials"]:
                failures.append(f"{case['id']}: trial count (expected {case['expected_trials']}, got {len(bundle.trials)})")
            else:
                passed += 1
        if "patient_index" in case:
            pid = bundle.patients[case["patient_index"] - 1].patient_id
            if pid != case["expected_id"]:
                failures.append(f"{case['id']}: expected {case['expected_id']} got {pid}")
            else:
                passed += 1

    trial_by_id = {t.nct_id: t for t in bundle.trials}
    for case in RET_CASES:
        patient = get_patient(bundle, case["patient_id"])
        trial = trial_by_id[case["nct_id"]]
        pack = build_evidence_bundle(patient, trial)
        ps = pack["patient_snippet"]
        if case.get("expect_hba1c_evidence") and not ps.get("hba1c_evidence_id"):
            failures.append(f"{case['id']}: missing hba1c evidence")
            continue
        if not case.get("expect_hba1c_evidence") and ps.get("hba1c_evidence_id"):
            failures.append(f"{case['id']}: unexpected hba1c evidence")
            continue
        if pack["trial_snippet"]["eligibility_source_id"] != case["expect_eligibility_source"]:
            failures.append(f"{case['id']}: eligibility source id")
            continue
        passed += 1

    for case in CRIT_CASES:
        patient = get_patient(bundle, case["patient_id"])
        trial = trial_by_id[case["nct_id"]]
        pack = build_evidence_bundle(patient, trial)
        fn = {
            "age": age.evaluate,
            "trial_recruiting_status": recruiting.evaluate,
            "egfr": egfr.evaluate,
            "hba1c": hba1c.evaluate,
        }[case["criterion"]]
        result = fn(pack)
        if result.state.value != case["expected_state"]:
            failures.append(
                f"{case['id']}: {case['criterion']} expected {case['expected_state']} got {result.state.value}"
            )
        else:
            passed += 1

    etc_scores: list[float] = []
    for case in AGENT_CASES:
        patient = get_patient(bundle, case["patient_id"])
        out = app.invoke({"patient_id": patient.patient_id, "patient": patient, "all_trials": bundle.trials})
        report = out["report"].to_json_dict()
        case_failed = False
        if len(report["matches"]) > case["max_matches"]:
            failures.append(f"{case['id']}: too many matches")
            case_failed = True
        if not case_failed and len(out.get("shortlisted_trial_ids") or []) < case.get("min_shortlisted", 0):
            failures.append(f"{case['id']}: shortlist too small")
            case_failed = True
        if not case_failed and case.get("require_traceability"):
            etc = evidence_traceability_completeness(report)
            etc_scores.append(etc)
            if etc < 1.0:
                failures.append(f"{case['id']}: ETC {etc:.2f} < 1.0")
                case_failed = True
        if not case_failed:
            passed += 1

    print(f"Eval summary: {passed} passed, {len(failures)} failed")
    for f in failures:
        print(f"  FAIL: {f}")
    if etc_scores:
        print(f"Sample ETC (evidence traceability): {sum(etc_scores)/len(etc_scores):.3f}")

    results_path = Path(__file__).parent / "results.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results_path.write_text(
        f"# Eval run\n\n_Run at: {timestamp}_\n\n- Passed: {passed}\n- Failed: {len(failures)}\n\n"
        + ("\n".join(f"- {f}" for f in failures) if failures else "All cases passed.\n"),
        encoding="utf-8",
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
