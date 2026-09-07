"""HbA1c eligibility vs latest patient lab."""

from __future__ import annotations

import re

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from state import TrialEvidenceBundle
from utils.llm_client import invoke_structured, llm_enabled

SYSTEM_PROMPT = """You compare a patient's HbA1c lab value(s) to trial eligibility text.
Rules:
- Missing patient HbA1c -> UNKNOWN (never SUPPORTED or NOT_SUPPORTED).
- Multiple patient values that imply different conclusions -> CONFLICTING_EVIDENCE.
- Complex or ambiguous trial wording -> REQUIRES_CLINICAL_REVIEW.
- Cite evidence_ids from the provided snippets only."""


class _HbA1cLLMResult(CriterionEvaluation):
    pass


def _parse_hba1c_thresholds(text: str) -> list[tuple[str, float]]:
    """Return list of (operator, threshold_percent) from common patterns."""
    found: list[tuple[str, float]] = []
    if not text:
        return found
    patterns = [
        (r"HbA1c\s*[≥>=\\>]+\s*(\d+(?:\.\d+)?)\s*%", "min"),
        (r"HbA1c\s*[≤<=\\<]+\s*(\d+(?:\.\d+)?)\s*%", "max"),
        (r"A1c\s*[≥>=\\>]+\s*(\d+(?:\.\d+)?)\s*%", "min"),
        (r"A1c\s*[≤<=\\<]+\s*(\d+(?:\.\d+)?)\s*%", "max"),
        (r"between\s+(\d+(?:\.\d+)?)\s*%?\s+and\s+(\d+(?:\.\d+)?)\s*%", "range"),
        (r"HbA1c levels between\s+(\d+(?:\.\d+)?)\s*%?\s+and\s+(\d+(?:\.\d+)?)", "range"),
    ]
    for pat, kind in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            if kind == "range" and len(m.groups()) >= 2:
                found.append(("range_min", float(m.group(1))))
                found.append(("range_max", float(m.group(2))))
            elif m.group(1):
                found.append((kind, float(m.group(1))))
    return found


def _rule_based(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    ps = bundle["patient_snippet"]
    ts = bundle["trial_snippet"]
    excerpt = ts.get("hba1c_related_excerpt") or ""
    evidence: list[str] = []
    if ps.get("hba1c_evidence_id"):
        evidence.append(ps["hba1c_evidence_id"])
    for row in ps.get("all_hba1c") or []:
        if row.get("source_id"):
            evidence.append(row["source_id"])
    evidence.append(ts["eligibility_source_id"])

    trial_requirement = excerpt.strip() or "No HbA1c-specific requirement extracted from eligibility text."

    values = [row for row in (ps.get("all_hba1c") or []) if row.get("value") is not None]
    if not values:
        return CriterionEvaluation(
            criterion="hba1c",
            state=CriterionState.UNKNOWN,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason="No HbA1c observation is established in the patient record.",
            evidence_ids=sorted(set(evidence)),
        )

    latest = ps.get("latest_hba1c")
    patient_value = latest

    # Safety: detect if excerpt discusses conditions affecting HbA1c measurement
    # accuracy (blood disorders, hemolysis, etc.) rather than a numeric threshold.
    if re.search(
        r"interfere|accuracy|disorder|dyscrasia|hemolysis|sickle.?cell",
        excerpt,
        re.IGNORECASE,
    ):
        return CriterionEvaluation(
            criterion="hba1c",
            state=CriterionState.REQUIRES_CLINICAL_REVIEW,
            patient_value=patient_value,
            trial_requirement=(
                "Trial mentions conditions affecting HbA1c measurement accuracy "
                "rather than a numeric threshold."
            ),
            reason=(
                "Eligibility text references conditions affecting HbA1c reliability "
                "(e.g., blood disorders, hemolysis); deferring to clinical review."
            ),
            evidence_ids=sorted(set(evidence)),
        )

    thresholds = _parse_hba1c_thresholds(excerpt)
    if not thresholds and "hba1c" not in excerpt.lower() and "a1c" not in excerpt.lower():
        if re.search(r"hba1c|a1c|hemoglobin", bundle["trial"].eligibility_text or "", re.I):
            return CriterionEvaluation(
                criterion="hba1c",
                state=CriterionState.REQUIRES_CLINICAL_REVIEW,
                patient_value=patient_value,
                trial_requirement="Trial mentions glycemic criteria but automated parsing could not extract a numeric rule.",
                reason="Eligibility references HbA1c with non-numeric or complex logic; defer to clinician.",
                evidence_ids=sorted(set(evidence)),
            )
        return CriterionEvaluation(
            criterion="hba1c",
            state=CriterionState.UNKNOWN,
            patient_value=patient_value,
            trial_requirement="No explicit HbA1c threshold found in retrieved eligibility excerpt.",
            reason="Trial record does not establish an automatable HbA1c rule in the retrieved text.",
            evidence_ids=sorted(set(evidence)),
        )

    if len(values) >= 2:
        low = min(v["value"] for v in values)
        high = max(v["value"] for v in values)
        if high - low >= 0.5:
            return CriterionEvaluation(
                criterion="hba1c",
                state=CriterionState.CONFLICTING_EVIDENCE,
                patient_value={"latest": patient_value, "range_in_record": [low, high]},
                trial_requirement=trial_requirement,
                reason=f"Patient record contains HbA1c values spanning {low}% to {high}%, which may support different conclusions.",
                evidence_ids=sorted(set(evidence)),
            )

    val = float(patient_value) if patient_value is not None else float(values[0]["value"])
    range_min = range_max = None
    min_t = max_t = None
    for op, thr in thresholds:
        if op == "min":
            min_t = thr if min_t is None else max(min_t, thr)
        elif op == "max":
            max_t = thr if max_t is None else min(max_t, thr)
        elif op == "range_min":
            range_min = thr
        elif op == "range_max":
            range_max = thr

    if range_min is not None and range_max is not None:
        if range_min <= val <= range_max:
            state = CriterionState.SUPPORTED
            reason = f"Patient HbA1c {val}% is within the trial range {range_min}-{range_max}%."
        else:
            state = CriterionState.NOT_SUPPORTED
            reason = f"Patient HbA1c {val}% is outside the trial range {range_min}-{range_max}%."
        return CriterionEvaluation(
            criterion="hba1c",
            state=state,
            patient_value=val,
            trial_requirement=f"HbA1c between {range_min}% and {range_max}%",
            reason=reason,
            evidence_ids=sorted(set(evidence)),
        )

    supported = True
    reasons: list[str] = []
    if min_t is not None:
        ok = val >= min_t
        supported = supported and ok
        reasons.append(f"{val}% {'≥' if ok else '<'} required minimum {min_t}%")
    if max_t is not None:
        ok = val <= max_t
        supported = supported and ok
        reasons.append(f"{val}% {'≤' if ok else '>'} required maximum {max_t}%")

    return CriterionEvaluation(
        criterion="hba1c",
        state=CriterionState.SUPPORTED if supported else CriterionState.NOT_SUPPORTED,
        patient_value=val,
        trial_requirement=trial_requirement,
        reason="; ".join(reasons) if reasons else f"Compared patient HbA1c {val}% to parsed trial thresholds.",
        evidence_ids=sorted(set(evidence)),
    )


def evaluate(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    if llm_enabled():
        ps = bundle["patient_snippet"]
        ts = bundle["trial_snippet"]
        user = f"Patient snippet:\n{ps}\n\nTrial HbA1c excerpt:\n{ts.get('hba1c_related_excerpt')}"
        try:
            result = invoke_structured(SYSTEM_PROMPT, user, CriterionEvaluation)
            result.criterion = "hba1c"
            return result
        except Exception:
            pass
    return _rule_based(bundle)
