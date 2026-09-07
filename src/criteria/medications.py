"""Current diabetes medications vs trial inclusion/exclusion medication language."""

from __future__ import annotations

import re

from criteria.states import CriterionState
from models.evaluation import CriterionEvaluation
from state import TrialEvidenceBundle
from utils.llm_client import invoke_structured, llm_enabled

SYSTEM_PROMPT = """Evaluate whether the patient's active medications conflict with trial eligibility.
Use medication names from the patient snippet and medication-related trial excerpt only.
If medications are missing -> UNKNOWN for medication-based conclusions.
If trial requires specific therapy the record cannot confirm -> UNKNOWN or REQUIRES_CLINICAL_REVIEW.
Never invent medications."""


EXCLUSION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"sulfonylurea", re.I), "sulfonylurea"),
    (re.compile(r"sglt-?2", re.I), "sglt2"),
    (re.compile(r"glp-?1", re.I), "glp1"),
    (re.compile(r"insulin", re.I), "insulin"),
    (re.compile(r"semaglutide", re.I), "semaglutide"),
    (re.compile(r"empagliflozin", re.I), "empagliflozin"),
    (re.compile(r"metformin", re.I), "metformin"),
]


def _med_matches_class(name: str, med_class: str) -> bool:
    n = name.lower()
    if med_class == "sglt2":
        return "empagliflozin" in n or "dapagliflozin" in n or "sglt" in n or "flozin" in n
    if med_class == "glp1":
        return "semaglutide" in n or "liraglutide" in n or "glp" in n or "tirzepatide" in n
    if med_class == "sulfonylurea":
        return "glipizide" in n or "glyburide" in n or "glimepiride" in n or "sulfonylurea" in n
    if med_class == "insulin":
        return "insulin" in n
    if med_class == "semaglutide":
        return "semaglutide" in n
    if med_class == "empagliflozin":
        return "empagliflozin" in n
    if med_class == "metformin":
        return "metformin" in n
    return med_class in n


def _rule_based(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    ps = bundle["patient_snippet"]
    ts = bundle["trial_snippet"]
    excerpt = ts.get("medication_related_excerpt") or ""
    meds = ps.get("active_medications") or []
    evidence = [m["source_id"] for m in meds if m.get("source_id")]
    evidence.append(ts["eligibility_source_id"])

    trial_requirement = excerpt.strip() or "No medication-specific requirement in retrieved excerpt."

    if not excerpt:
        return CriterionEvaluation(
            criterion="current_diabetes_medications",
            state=CriterionState.UNKNOWN,
            patient_value=[m.get("name") for m in meds] or None,
            trial_requirement="No medication eligibility language retrieved.",
            reason="Trial excerpt does not establish medication rules for automated comparison.",
            evidence_ids=sorted(set(evidence)),
        )

    excluded_classes: list[str] = []
    for pat, label in EXCLUSION_PATTERNS:
        if pat.search(excerpt) and re.search(r"exclud|not allowed|prohibited|must not|without", excerpt, re.I):
            if label not in excluded_classes:
                excluded_classes.append(label)

    patient_names = [m.get("name", "") for m in meds]
    if not patient_names:
        if re.search(r"insulin|medication|therapy", excerpt, re.I):
            return CriterionEvaluation(
                criterion="current_diabetes_medications",
                state=CriterionState.UNKNOWN,
                patient_value=None,
                trial_requirement=trial_requirement,
                reason="Trial eligibility references therapy but no active medications are established in the patient record.",
                evidence_ids=sorted(set(evidence)),
            )
        return CriterionEvaluation(
            criterion="current_diabetes_medications",
            state=CriterionState.UNKNOWN,
            patient_value=None,
            trial_requirement=trial_requirement,
            reason="Patient medication list is empty in the supplied record.",
            evidence_ids=sorted(set(evidence)),
        )

    conflicts: list[str] = []
    for med_class in excluded_classes:
        for name in patient_names:
            if _med_matches_class(name, med_class):
                conflicts.append(f"{name} (matches excluded class {med_class})")

    if conflicts:
        return CriterionEvaluation(
            criterion="current_diabetes_medications",
            state=CriterionState.NOT_SUPPORTED,
            patient_value=patient_names,
            trial_requirement=trial_requirement,
            reason="Active medication(s) appear to conflict with trial exclusion language: " + "; ".join(conflicts),
            evidence_ids=sorted(set(evidence)),
        )

    if re.search(r"must include|requires|treated with|on current.*insulin", excerpt, re.I):
        required = []
        for pat, label in EXCLUSION_PATTERNS:
            if pat.search(excerpt) and re.search(r"require|must|include|treated", excerpt, re.I):
                required.append(label)
        unmet = [label for label in required if not any(_med_matches_class(n, label) for n in patient_names)]
        if unmet:
            return CriterionEvaluation(
                criterion="current_diabetes_medications",
                state=CriterionState.NOT_SUPPORTED,
                patient_value=patient_names,
                trial_requirement=trial_requirement,
                reason=f"Trial appears to require {', '.join(unmet)} therapy not reflected in active medications.",
                evidence_ids=sorted(set(evidence)),
            )

    if len(excerpt) > 400 and re.search(r"medication|insulin|therapy", excerpt, re.I):
        return CriterionEvaluation(
            criterion="current_diabetes_medications",
            state=CriterionState.REQUIRES_CLINICAL_REVIEW,
            patient_value=patient_names,
            trial_requirement=trial_requirement,
            reason="Medication eligibility language is extensive; automated keyword pass found no definite conflict or match.",
            evidence_ids=sorted(set(evidence)),
        )

    return CriterionEvaluation(
        criterion="current_diabetes_medications",
        state=CriterionState.REQUIRES_CLINICAL_REVIEW,
        patient_value=patient_names,
        trial_requirement=trial_requirement,
        reason="Medication eligibility text could not be confidently mapped to the patient's active medications using deterministic rules. Manual clinical review is required.",
        evidence_ids=sorted(set(evidence)),
    )


def evaluate(bundle: TrialEvidenceBundle) -> CriterionEvaluation:
    if llm_enabled():
        ps = bundle["patient_snippet"]
        ts = bundle["trial_snippet"]
        user = f"Patient meds:\n{ps.get('active_medications')}\n\nTrial excerpt:\n{ts.get('medication_related_excerpt')}"
        try:
            result = invoke_structured(SYSTEM_PROMPT, user, CriterionEvaluation)
            result.criterion = "current_diabetes_medications"
            return result
        except Exception:
            pass
    return _rule_based(bundle)
