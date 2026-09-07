"""eGFR / renal function eligibility."""

from __future__ import annotations

import re

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from state import TrialEvidenceBundle
from utils.llm_client import invoke_structured, llm_enabled

SYSTEM_PROMPT = """Compare patient eGFR/GFR to trial renal eligibility text.
Missing patient eGFR -> UNKNOWN. Never guess renal function.
Use CONFLICTING_EVIDENCE if patient labs conflict. Complex trial rules -> REQUIRES_CLINICAL_REVIEW."""


def _extract_gfr_rules(text: str) -> list[str]:
    if not text:
        return []
    rules: list[str] = []
    for m in re.finditer(
        r"(GFR|eGFR|creatinine clearance)[^.\n]{0,80}(\d+)[^.\n]{0,40}(ml/min|mL/min)",
        text,
        re.IGNORECASE,
    ):
        rules.append(m.group(0))
    return rules


def _rule_based(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    ps = bundle["patient_snippet"]
    ts = bundle["trial_snippet"]
    excerpt = ts.get("egfr_related_excerpt") or ""
    evidence: list[str] = []
    if ps.get("egfr_evidence_id"):
        evidence.append(ps["egfr_evidence_id"])
    evidence.append(ts["eligibility_source_id"])

    patient_value = ps.get("latest_egfr")
    missing_domain = "egfr" in (ps.get("record_quality") or {}).get("missing_expected_domains", [])
    trial_requirement = excerpt.strip() or "No eGFR/GFR-specific requirement in retrieved excerpt."

    if patient_value is None:
        state = CriterionState.UNKNOWN
        reason = "No eGFR observation is established in the patient record."
        if missing_domain:
            reason += " Record quality flags eGFR as a missing expected domain."
        return CriterionEvaluation(
            criterion="egfr",
            state=state,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason=reason,
            evidence_ids=sorted(set(evidence)),
        )

    rules = _extract_gfr_rules(excerpt)
    if not rules:
        if re.search(r"gfr|egfr|renal|kidney|creatinine", bundle["trial"].eligibility_text or "", re.I):
            return CriterionEvaluation(
                criterion="egfr",
                state=CriterionState.REQUIRES_CLINICAL_REVIEW,
                patient_value=patient_value,
                trial_requirement="Trial references renal function with complex or non-numeric criteria.",
                reason=f"Patient eGFR is {patient_value} mL/min/1.73m² but trial renal rules need clinical interpretation.",
                evidence_ids=sorted(set(evidence)),
            )
        return CriterionEvaluation(
            criterion="egfr",
            state=CriterionState.UNKNOWN,
            patient_value=patient_value,
            trial_requirement="No automatable eGFR threshold in retrieved eligibility excerpt.",
            reason="Trial record does not establish a numeric eGFR rule in the retrieved text.",
            evidence_ids=sorted(set(evidence)),
        )

    # Safety: detect if the GFR rule lives in the Exclusion Criteria section.
    # Exclusion-framed thresholds (e.g. "exclude if eGFR < 30") require inverted
    # comparison logic that our simple parser cannot reliably handle.
    full_elig_lower = (bundle["trial"].eligibility_text or "").lower()
    exc_idx = full_elig_lower.find("exclusion criteria")
    if exc_idx >= 0:
        exclusion_section = full_elig_lower[exc_idx:]
        if re.search(r"(?:e?gfr|creatinine clearance|gfr)\s*[<≤\\<]", exclusion_section):
            return CriterionEvaluation(
                criterion="egfr",
                state=CriterionState.REQUIRES_CLINICAL_REVIEW,
                patient_value=patient_value,
                trial_requirement=trial_requirement,
                reason=(
                    "Renal function criterion appears under the trial's exclusion criteria. "
                    "Automated threshold parsing may misinterpret inclusion vs. exclusion "
                    "direction; deferring to clinical review."
                ),
                evidence_ids=sorted(set(evidence)),
            )

    # Parse minimum GFR requirements
    mins: list[float] = []
    for rule in rules:
        nums = re.findall(r"(\d+)\s*mL/min", rule, re.I)
        for n in nums:
            val = float(n)
            if "<" in rule or "≤" in rule or "under" in rule.lower():
                mins.append(val)
            elif ">" in rule or "≥" in rule:
                mins.append(val)

    if not mins:
        return CriterionEvaluation(
            criterion="egfr",
            state=CriterionState.REQUIRES_CLINICAL_REVIEW,
            patient_value=patient_value,
            trial_requirement=trial_requirement,
            reason="Renal eligibility language was found but could not be reduced to a single numeric comparison.",
            evidence_ids=sorted(set(evidence)),
        )

    threshold = max(mins)
    if patient_value >= threshold:
        state = CriterionState.SUPPORTED
        reason = f"Patient eGFR {patient_value} mL/min/1.73m² meets parsed minimum threshold {threshold}."
    else:
        state = CriterionState.NOT_SUPPORTED
        reason = f"Patient eGFR {patient_value} mL/min/1.73m² is below parsed threshold {threshold}."

    return CriterionEvaluation(
        criterion="egfr",
        state=state,
        patient_value=patient_value,
        trial_requirement=trial_requirement,
        reason=reason,
        evidence_ids=sorted(set(evidence)),
    )


def evaluate(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    if llm_enabled():
        ps = bundle["patient_snippet"]
        ts = bundle["trial_snippet"]
        user = f"Patient snippet:\n{ps}\n\nTrial renal excerpt:\n{ts.get('egfr_related_excerpt')}"
        try:
            result = invoke_structured(SYSTEM_PROMPT, user, CriterionEvaluation)
            result.criterion = "egfr"
            return result
        except Exception:
            pass
    return _rule_based(bundle)
