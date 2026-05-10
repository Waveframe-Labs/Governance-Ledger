"""Deterministic authoring validation for governance policy text."""

from __future__ import annotations

import re
from typing import Any

from governance_ledger.extract import _normalize_text
from governance_ledger.patterns import (
    AMBIGUOUS_AUTHORITY_PATTERNS,
    GOVERNANCE_SIGNAL_PATTERN,
    ROLE_PATTERNS,
    SEPARATION_PATTERNS,
    THRESHOLD_PATTERNS,
    UNSUPPORTED_CONSTRAINT_PATTERNS,
)

ALLOWED_COMPILER_POLICY_KEYS = {
    "contract_id",
    "contract_version",
    "authority",
    "artifacts",
    "approvals",
    "stages",
}


def validate_authoring(text: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Surface unsupported, ambiguous, or unextracted governance language."""
    normalized_text = _normalize_text(text)
    warnings: list[dict[str, str]] = []

    for pattern in UNSUPPORTED_CONSTRAINT_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            _append_unique_warning(
                warnings,
                {
                    "type": "unsupported_constraint",
                    "severity": "warning",
                    "text": match.group(0),
                },
            )

    for pattern in AMBIGUOUS_AUTHORITY_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            _append_unique_warning(
                warnings,
                {
                    "type": "ambiguous_authority",
                    "severity": "error",
                    "text": match.group(0),
                },
            )

    covered_spans = _covered_spans(normalized_text)
    warned_spans = _warning_spans(normalized_text)
    for sentence in _governance_sentences(normalized_text):
        if _has_overlap(sentence["span"], covered_spans) or _has_overlap(sentence["span"], warned_spans):
            continue
        _append_unique_warning(
            warnings,
            {
                "type": "extraction_gap",
                "severity": "warning",
                "text": sentence["text"],
            },
        )

    if policy is not None:
        for warning in validate_compiler_policy(policy)["warnings"]:
            _append_unique_warning(warnings, warning)

    return {"warnings": warnings}


def validate_compiler_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Validate extracted policy against the canonical compiler ingestion schema."""
    warnings: list[dict[str, str]] = []

    _validate_required_string(policy, "contract_id", warnings)
    _validate_required_string(policy, "contract_version", warnings)
    if isinstance(policy.get("contract_version"), str) and not re.match(
        r"^[0-9]+\.[0-9]+\.[0-9]+$",
        policy["contract_version"],
    ):
        _append_schema_error(warnings, "contract_version must be a semantic version.")

    for key in policy:
        if key not in ALLOWED_COMPILER_POLICY_KEYS:
            _append_schema_error(warnings, f"additional property is not allowed: {key}")

    if "authority" in policy:
        _validate_authority(policy["authority"], warnings)
    if "artifacts" in policy:
        _validate_artifacts(policy["artifacts"], warnings)
    if "approvals" in policy:
        _validate_approvals(policy["approvals"], warnings)
    if "stages" in policy:
        _validate_stages(policy["stages"], warnings)

    return {"warnings": warnings}


def has_validation_errors(validation: dict[str, Any]) -> bool:
    return any(warning.get("severity") == "error" for warning in validation.get("warnings", []))


def _covered_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in [*ROLE_PATTERNS, *SEPARATION_PATTERNS, *THRESHOLD_PATTERNS]:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append(match.span())
    return spans


def _warning_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for pattern in [*UNSUPPORTED_CONSTRAINT_PATTERNS, *AMBIGUOUS_AUTHORITY_PATTERNS]:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append(match.span())
    return spans


def _governance_sentences(text: str) -> list[dict[str, Any]]:
    sentences: list[dict[str, Any]] = []
    for match in re.finditer(r"[^.!?]+[.!?]?", text):
        sentence = match.group(0).strip()
        if sentence and re.search(GOVERNANCE_SIGNAL_PATTERN, sentence, flags=re.IGNORECASE):
            sentences.append({"text": sentence, "span": match.span()})
    return sentences


def _has_overlap(span: tuple[int, int], spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < covered_end and end > covered_start for covered_start, covered_end in spans)


def _append_unique_warning(warnings: list[dict[str, str]], warning: dict[str, str]) -> None:
    if warning not in warnings:
        warnings.append(warning)


def _append_schema_error(warnings: list[dict[str, str]], text: str) -> None:
    _append_unique_warning(
        warnings,
        {
            "type": "compiler_schema",
            "severity": "error",
            "text": text,
        },
    )


def _validate_required_string(
    payload: dict[str, Any],
    field: str,
    warnings: list[dict[str, str]],
) -> None:
    if not isinstance(payload.get(field), str) or not payload.get(field):
        _append_schema_error(warnings, f"{field} is required and must be a string.")


def _validate_object(
    value: Any,
    field: str,
    warnings: list[dict[str, str]],
) -> bool:
    if not isinstance(value, dict):
        _append_schema_error(warnings, f"{field} must be an object.")
        return False
    return True


def _validate_string_array(
    payload: dict[str, Any],
    field: str,
    warnings: list[dict[str, str]],
    *,
    label: str | None = None,
) -> None:
    display = label or field
    value = payload.get(field)
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        _append_schema_error(warnings, f"{display} must be an array of strings.")
    elif len(value) != len(set(value)):
        _append_schema_error(warnings, f"{display} must contain unique items.")


def _validate_authority(authority: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(authority, "authority", warnings):
        return
    for key in authority:
        if key not in {"required_roles", "separation_of_duties"}:
            _append_schema_error(warnings, f"authority additional property is not allowed: {key}")
    if "required_roles" in authority:
        _validate_string_array(authority, "required_roles", warnings, label="authority.required_roles")
    if "separation_of_duties" in authority and not isinstance(authority["separation_of_duties"], bool):
        _append_schema_error(warnings, "authority.separation_of_duties must be a boolean.")


def _validate_artifacts(artifacts: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(artifacts, "artifacts", warnings):
        return
    for key in artifacts:
        if key != "required":
            _append_schema_error(warnings, f"artifacts additional property is not allowed: {key}")
    if "required" in artifacts:
        _validate_string_array(artifacts, "required", warnings, label="artifacts.required")


def _validate_approvals(approvals: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(approvals, "approvals", warnings):
        return
    for key in approvals:
        if key != "thresholds":
            _append_schema_error(warnings, f"approvals additional property is not allowed: {key}")
    thresholds = approvals.get("thresholds")
    if "thresholds" in approvals and not isinstance(thresholds, list):
        _append_schema_error(warnings, "approvals.thresholds must be an array.")
        return
    for threshold in thresholds or []:
        _validate_threshold(threshold, warnings)


def _validate_threshold(threshold: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(threshold, "approvals.thresholds[]", warnings):
        return
    required = {"field", "operator", "value", "requires_role"}
    for field in required:
        if field not in threshold:
            _append_schema_error(warnings, f"approvals.thresholds[] missing required field: {field}")
    for key in threshold:
        if key not in required:
            _append_schema_error(warnings, f"approvals.thresholds[] additional property is not allowed: {key}")
    for field in {"field", "operator", "requires_role"}:
        if field in threshold and not isinstance(threshold[field], str):
            _append_schema_error(warnings, f"approvals.thresholds[].{field} must be a string.")


def _validate_stages(stages: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(stages, "stages", warnings):
        return
    for key in stages:
        if key != "allowed_transitions":
            _append_schema_error(warnings, f"stages additional property is not allowed: {key}")
    transitions = stages.get("allowed_transitions")
    if "allowed_transitions" in stages and not isinstance(transitions, list):
        _append_schema_error(warnings, "stages.allowed_transitions must be an array.")
        return
    for transition in transitions or []:
        if not _validate_object(transition, "stages.allowed_transitions[]", warnings):
            continue
        for field in {"from", "to"}:
            if not isinstance(transition.get(field), str):
                _append_schema_error(
                    warnings,
                    f"stages.allowed_transitions[].{field} is required and must be a string.",
                )
        for key in transition:
            if key not in {"from", "to"}:
                _append_schema_error(
                    warnings,
                    f"stages.allowed_transitions[] additional property is not allowed: {key}",
                )
