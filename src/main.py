#!/usr/bin/env python3
"""CLI entry: run the 4-node pre-screening graph for one patient."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow running as `python main.py` from src/
_SRC = Path(__file__).resolve().parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph import build_graph  # noqa: E402
from utils.data_loader import get_patient, load_dataset, resolve_patient_id  # noqa: E402


def main() -> int:
    load_dotenv(_SRC.parent / ".env")
    parser = argparse.ArgumentParser(description="Type 2 diabetes trial pre-screening agent")
    parser.add_argument("--patient_id", required=True, help="Dataset id (P-2715) or shorthand (P03)")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Path to Type2-Diabetes-Trial-Agent-Dataset.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write JSON report to this path (default: stdout only)",
    )
    args = parser.parse_args()

    bundle = load_dataset(args.dataset)
    patient = get_patient(bundle, args.patient_id)
    resolved_id = resolve_patient_id(args.patient_id, bundle.patients)

    app = build_graph()
    final = app.invoke(
        {
            "patient_id": resolved_id,
            "patient": patient,
            "all_trials": bundle.trials,
        }
    )
    report = final["report"]
    payload = report.to_json_dict()
    text = json.dumps(payload, indent=2)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print(f"Wrote report to {args.output}", file=sys.stderr)
    else:
        print(text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
