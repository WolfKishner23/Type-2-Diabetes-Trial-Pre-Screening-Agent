"""
Evidence Traceability Completeness (ETC) — original metric.

Failure hypothesis: The agent will produce plausible natural-language reasons while omitting
evidence_ids on one or more criterion results, breaking auditability required for pre-screening.

Baseline: fraction of criterion evaluations with >=1 evidence_id (micro-average across all
criteria for a patient run).

ETC = (# criterion results with non-empty evidence_ids) / (# criterion results)

Limitations:
- Does not measure whether evidence_ids are *correct*, only present.
- Weighting all criteria equally ignores that recruiting/age may be easier to cite than medications.
- Rule-based paths always cite IDs, so ETC may overstate quality when LLM mode omits IDs.
"""

from __future__ import annotations

from typing import Any


def evidence_traceability_completeness(report: dict[str, Any]) -> float:
    total = 0
    with_ids = 0
    for match in report.get("matches", []):
        for cr in match.get("criterion_results", []):
            total += 1
            if cr.get("evidence_ids"):
                with_ids += 1
    if total == 0:
        return 1.0
    return with_ids / total


def baseline_always_unknown(report: dict[str, Any]) -> float:
    """Straw baseline: score 1.0 only if every criterion is UNKNOWN (not useful clinically)."""
    total = 0
    unknown = 0
    for match in report.get("matches", []):
        for cr in match.get("criterion_results", []):
            total += 1
            if cr.get("state") == "UNKNOWN":
                unknown += 1
    if total == 0:
        return 0.0
    return unknown / total
