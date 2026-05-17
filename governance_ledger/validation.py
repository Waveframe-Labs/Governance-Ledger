"""Deterministic authoring validation for governance policy text."""

from __future__ import annotations

import re
from typing import Any

from governance_ledger.diagnostics import build_diagnostic
from governance_ledger.patterns import (
    AMBIGUOUS_AUTHORITY_PATTERNS,
    AMBIGUOUS_PROCESS_PATTERNS,
    AMBIGUOUS_RISK_PATTERNS,
    AMBIGUOUS_TEMPORAL_PATTERNS,
    AMBIGUOUS_THRESHOLD_PATTERNS,
    MISSING_ROLE_THRESHOLD_PATTERNS,
    UNSUPPORTED_CONSTRAINT_PATTERNS,
)
from governance_ledger.statement_normalizer import normalize_governance_statements, normalize_text

ALLOWED_COMPILER_POLICY_KEYS = {
    "contract_id",
    "contract_version",
    "authority",
    "artifacts",
    "approvals",
    "stages",
}

MIN_NORMALIZATION_COVERAGE = 0.8


def validate_authoring(text: str, policy: dict[str, Any] | None = None) -> dict[str, Any]:
    """Surface unsupported, ambiguous, or unextracted governance language."""
    normalized_text = normalize_text(text)
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

    for warning_type, patterns, message in [
        ("ambiguous_authority", AMBIGUOUS_AUTHORITY_PATTERNS, "authority is unresolved"),
        ("ambiguous_threshold", AMBIGUOUS_THRESHOLD_PATTERNS, "threshold is subjective or incomplete"),
        ("ambiguous_temporal", AMBIGUOUS_TEMPORAL_PATTERNS, "timing is subjective or incomplete"),
        ("ambiguous_risk", AMBIGUOUS_RISK_PATTERNS, "risk tier is subjective or incomplete"),
        ("ambiguous_process", AMBIGUOUS_PROCESS_PATTERNS, "approval process is subjective or incomplete"),
    ]:
        for pattern in patterns:
            for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
                _append_unique_warning(
                    warnings,
                    {
                        "type": warning_type,
                        "severity": "error",
                        "text": f"{match.group(0)}: {message}",
                    },
                )

    for pattern in MISSING_ROLE_THRESHOLD_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            _append_unique_warning(
                warnings,
                {
                    "type": "ambiguous_authority",
                    "severity": "error",
                    "text": f"{match.group('source')} requires approval but does not name the approving role",
                },
            )

    normalized_statements = normalize_governance_statements(normalized_text)
    warned_spans = _warning_spans(normalized_text)
    governance_sentences = [
        {
            "text": statement["text"],
            "span": statement["span"],
            "normalized_statement": statement["normalized_statement"],
        }
        for statement in normalized_statements
    ]
    coverage = _normalization_coverage(governance_sentences)
    if (
        coverage["detected_governance_statements"] > 0
        and coverage["coverage"] < MIN_NORMALIZATION_COVERAGE
    ):
        _append_unique_warning(
            warnings,
            {
                "type": "normalization_coverage",
                "severity": "error",
                "text": (
                    "Governance normalization coverage below required threshold: "
                    f"{coverage['deterministically_normalized']} of "
                    f"{coverage['detected_governance_statements']} statements normalized "
                    f"({coverage['coverage_percent']}%)."
                ),
            },
        )

    for sentence in governance_sentences:
        if sentence["normalized_statement"] or _has_overlap(sentence["span"], warned_spans):
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
        for warning in validate_extraction_integrity(normalized_text, policy)["warnings"]:
            _append_unique_warning(warnings, warning)
        for warning in validate_compiler_policy(policy)["warnings"]:
            _append_unique_warning(warnings, warning)
        for warning in validate_governance_consistency(normalized_text, policy)["warnings"]:
            _append_unique_warning(warnings, warning)
        for warning in validate_governance_lint(policy)["warnings"]:
            _append_unique_warning(warnings, warning)

    return {"warnings": warnings, "coverage": coverage}


def validate_governance_consistency(text: str, policy: dict[str, Any]) -> dict[str, Any]:
    """Emit compiler-style diagnostics for contradictory normalized governance."""
    warnings: list[dict[str, str]] = []
    _validate_threshold_consistency(policy, warnings)
    _validate_lifecycle_consistency(policy, warnings)
    _validate_artifact_consistency(text, warnings)
    _validate_role_integrity(policy, warnings)
    return {"warnings": warnings}


def validate_governance_lint(policy: dict[str, Any]) -> dict[str, Any]:
    """Emit non-fatal governance quality and maintainability diagnostics."""
    warnings: list[dict[str, str]] = []
    _lint_approval_paths(policy, warnings)
    _lint_policy_complexity(policy, warnings)
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


def validate_extraction_integrity(text: str, policy: dict[str, Any]) -> dict[str, Any]:
    """Detect deterministic governance phrases that only partially normalized."""
    warnings: list[dict[str, str]] = []
    role_threshold_matches = [
        statement
        for statement in normalize_governance_statements(text)
        if statement["classification"] == "conditional_threshold_approval"
    ]
    extracted_thresholds = policy.get("approvals", {}).get("thresholds", [])
    if role_threshold_matches and len(extracted_thresholds) < len(role_threshold_matches):
        _append_unique_warning(
            warnings,
            {
                "type": "partial_extraction_integrity",
                "severity": "error",
                "text": "Threshold phrase detected but deterministic threshold normalization did not complete.",
            },
        )

    required_roles = policy.get("authority", {}).get("required_roles", [])
    if required_roles and _contains_conditional_transfer_language(text) and not extracted_thresholds:
        _append_unique_warning(
            warnings,
            {
                "type": "partial_extraction_integrity",
                "severity": "error",
                "text": "Authority extracted without an enforceable transfer condition.",
            },
        )
    return {"warnings": warnings}


def has_validation_errors(validation: dict[str, Any]) -> bool:
    return any(warning.get("severity") == "error" for warning in validation.get("warnings", []))


def _validate_threshold_consistency(policy: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    thresholds = policy.get("approvals", {}).get("thresholds", [])
    ranges = [_threshold_range(threshold) for threshold in thresholds if isinstance(threshold, dict)]
    ranges = [item for item in ranges if item is not None]
    for index, left in enumerate(ranges):
        for right in ranges[index + 1:]:
            if left["field"] != right["field"]:
                continue
            if _ranges_overlap(left, right):
                _append_diagnostic(
                    warnings,
                    code="G102",
                    severity="error",
                    title="Overlapping approval authority ranges detected",
                    detail=(
                        f"{left['role']}: {_format_range(left)}; "
                        f"{right['role']}: {_format_range(right)}. "
                        "One execution amount could satisfy multiple approval authorities."
                    ),
                )
    ordered = sorted(ranges, key=lambda item: (item["field"], item["lower"]))
    for left, right in zip(ordered, ordered[1:]):
        if left["field"] != right["field"]:
            continue
        if _has_range_gap(left, right):
                _append_diagnostic(
                    warnings,
                    code="G103",
                    severity="warning",
                    title="Approval authority range gap detected",
                    detail=(
                        f"{left['role']}: {_format_range(left)}; "
                        f"{right['role']}: {_format_range(right)}. "
                        "Some execution amounts may have no explicit approval authority."
                    ),
                )


def _validate_lifecycle_consistency(policy: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    transitions = policy.get("stages", {}).get("allowed_transitions", [])
    graph: dict[str, list[str]] = {}
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        start = transition.get("from")
        end = transition.get("to")
        if not isinstance(start, str) or not isinstance(end, str):
            continue
        if start == end:
            _append_diagnostic(
                warnings,
                code="G302",
                severity="error",
                title="Impossible lifecycle transition detected",
                detail=f"{start} -> {end} loops to the same state.",
            )
        graph.setdefault(start, []).append(end)
        graph.setdefault(end, [])
    if _has_cycle(graph):
        _append_diagnostic(
            warnings,
            code="G301",
            severity="error",
            title="Illegal lifecycle cycle detected",
            detail="Governance stage transitions can return to a prior state.",
        )
    incoming = {node: 0 for node in graph}
    for targets in graph.values():
        for target in targets:
            incoming[target] = incoming.get(target, 0) + 1
    orphan_terminal = [
        node
        for node, targets in graph.items()
        if incoming.get(node, 0) == 0 and not targets and len(graph) > 1
    ]
    if orphan_terminal:
        _append_diagnostic(
            warnings,
            code="G303",
            severity="warning",
            title="Orphan lifecycle state detected",
            detail=f"State has no incoming or outgoing transition: {', '.join(sorted(orphan_terminal))}.",
        )


def _validate_artifact_consistency(text: str, warnings: list[dict[str, str]]) -> None:
    retain = _duration_years(
        re.search(r"\bretain(?:ed)?\b.*?\b(?P<value>\d+)\s+(?P<unit>days?|months?|years?)\b", text, flags=re.IGNORECASE)
    )
    delete = _duration_years(
        re.search(r"\bdelete(?:d)?\s+after\s+(?P<value>\d+)\s+(?P<unit>days?|months?|years?)\b", text, flags=re.IGNORECASE)
    )
    if retain is not None and delete is not None and delete < retain:
        _append_diagnostic(
            warnings,
            code="G401",
            severity="error",
            title="Contradictory artifact retention detected",
            detail="Deletion occurs before required retention expires.",
        )


def _validate_role_integrity(policy: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    required = policy.get("approvals", {}).get("required", [])
    required_roles = [
        approval.get("role")
        for approval in required
        if isinstance(approval, dict) and isinstance(approval.get("role"), str)
    ]
    if policy.get("authority", {}).get("separation_of_duties") is True and "requester" in required_roles:
        _append_diagnostic(
            warnings,
            code="G501",
            severity="error",
            title="Impossible role constraint detected",
            detail="Requester approval conflicts with separation of duties.",
        )
    if len(required_roles) != len(set(required_roles)):
        _append_diagnostic(
            warnings,
            code="G502",
            severity="warning",
            title="Duplicate required approval role detected",
            detail="Approval identity semantics are ambiguous for repeated required roles.",
            recommendation="Represent repeated approval requirements as distinct roles or conditions.",
        )


def _lint_approval_paths(policy: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    required = [
        approval
        for approval in policy.get("approvals", {}).get("required", [])
        if isinstance(approval, dict)
    ]
    conditional = [approval for approval in required if isinstance(approval.get("condition"), dict)]
    unconditional = [approval for approval in required if "condition" not in approval]
    if conditional and unconditional:
        _append_diagnostic(
            warnings,
            code="G701",
            severity="info",
            title="Cumulative approval path detected",
            detail=(
                "Policy combines unconditional and conditional approval requirements. "
                "This is operationally valid, but operators should understand that some executions require multiple approvals."
            ),
            recommendation="Make cumulative approval intent explicit in operator-facing policy text.",
        )


def _lint_policy_complexity(policy: dict[str, Any], warnings: list[dict[str, str]]) -> None:
    required = policy.get("approvals", {}).get("required", [])
    transitions = policy.get("stages", {}).get("allowed_transitions", [])
    artifact_count = len(policy.get("artifacts", {}).get("required", []))
    complexity = (
        len(required if isinstance(required, list) else [])
        + len(transitions if isinstance(transitions, list) else [])
        + artifact_count
    )
    if complexity > 5:
        _append_diagnostic(
            warnings,
            code="G702",
            severity="warning",
            title="Governance policy exceeds recommended complexity",
            detail=(
                f"Policy contains {complexity} normalized operational requirements. "
                "Large governance artifacts are harder to review, explain, and operate safely."
            ),
            recommendation="Consider splitting the policy into smaller authority artifacts.",
        )


def _threshold_range(threshold: dict[str, Any]) -> dict[str, Any] | None:
    operator = threshold.get("operator")
    value = threshold.get("value")
    if threshold.get("field") != "amount" or not isinstance(value, (int, float)):
        return None
    lower = float("-inf")
    upper = float("inf")
    lower_inclusive = False
    upper_inclusive = False
    if operator == ">":
        lower = value
    elif operator == ">=":
        lower = value
        lower_inclusive = True
    elif operator == "<":
        upper = value
    elif operator == "<=":
        upper = value
        upper_inclusive = True
    else:
        return None
    return {
        "field": threshold["field"],
        "role": threshold.get("requires_role", "unknown"),
        "lower": lower,
        "upper": upper,
        "lower_inclusive": lower_inclusive,
        "upper_inclusive": upper_inclusive,
    }


def _ranges_overlap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["upper"] < right["lower"] or right["upper"] < left["lower"]:
        return False
    if left["upper"] == right["lower"]:
        return left["upper_inclusive"] and right["lower_inclusive"]
    if right["upper"] == left["lower"]:
        return right["upper_inclusive"] and left["lower_inclusive"]
    return True


def _has_range_gap(left: dict[str, Any], right: dict[str, Any]) -> bool:
    if left["upper"] == float("inf") or right["lower"] == float("-inf"):
        return False
    if left["upper"] < right["lower"]:
        return True
    if left["upper"] == right["lower"]:
        return not (left["upper_inclusive"] or right["lower_inclusive"])
    return False


def _format_range(item: dict[str, Any]) -> str:
    lower = "-inf" if item["lower"] == float("-inf") else str(int(item["lower"]))
    upper = "inf" if item["upper"] == float("inf") else str(int(item["upper"]))
    left = "[" if item["lower_inclusive"] else "("
    right = "]" if item["upper_inclusive"] else ")"
    return f"{left}{lower}, {upper}{right}"


def _has_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for target in graph.get(node, []):
            if visit(target):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _duration_years(match: re.Match[str] | None) -> float | None:
    if not match:
        return None
    value = int(match.group("value"))
    unit = match.group("unit").lower()
    if unit.startswith("day"):
        return value / 365
    if unit.startswith("month"):
        return value / 12
    return float(value)


def _contains_conditional_transfer_language(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:large|material|significant|above|over|greater\s+than|exceeding|at\s+least|below|under|less\s+than)\s+"
            r"(?:transfers?|purchases?|payments?|invoices?|requests?)\b"
            r"|\b(?:transfers?|purchases?|payments?|invoices?|requests?)\s+"
            r"(?:large|material|significant|above|over|greater\s+than|exceeding|at\s+least|below|under|less\s+than)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _warning_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    ambiguous_patterns = [
        *AMBIGUOUS_AUTHORITY_PATTERNS,
        *AMBIGUOUS_THRESHOLD_PATTERNS,
        *AMBIGUOUS_TEMPORAL_PATTERNS,
        *AMBIGUOUS_RISK_PATTERNS,
        *AMBIGUOUS_PROCESS_PATTERNS,
    ]
    for pattern in [*UNSUPPORTED_CONSTRAINT_PATTERNS, *ambiguous_patterns, *MISSING_ROLE_THRESHOLD_PATTERNS]:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            spans.append(match.span())
    return spans


def _normalization_coverage(
    governance_sentences: list[dict[str, Any]],
) -> dict[str, Any]:
    detected = len(governance_sentences)
    normalized = sum(
        1
        for sentence in governance_sentences
        if sentence["normalized_statement"]
    )
    coverage = 1.0 if detected == 0 else normalized / detected
    return {
        "schema_version": "governance_normalization_coverage.v1",
        "detected_governance_statements": detected,
        "deterministically_normalized": normalized,
        "coverage": coverage,
        "coverage_percent": round(coverage * 100),
        "minimum_required": MIN_NORMALIZATION_COVERAGE,
        "minimum_required_percent": round(MIN_NORMALIZATION_COVERAGE * 100),
    }


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


def _append_diagnostic(
    warnings: list[dict[str, str]],
    *,
    code: str,
    severity: str,
    title: str,
    detail: str,
    recommendation: str | None = None,
) -> None:
    _append_unique_warning(
        warnings,
        build_diagnostic(
            code=code,
            severity=severity,
            title=title,
            detail=detail,
            recommendation=recommendation,
        ),
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
        if key not in {"required", "thresholds"}:
            _append_schema_error(warnings, f"approvals additional property is not allowed: {key}")
    required_approvals = approvals.get("required")
    if "required" in approvals and not isinstance(required_approvals, list):
        _append_schema_error(warnings, "approvals.required must be an array.")
    for approval in required_approvals or []:
        _validate_required_approval(approval, warnings)
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


def _validate_required_approval(approval: Any, warnings: list[dict[str, str]]) -> None:
    if not _validate_object(approval, "approvals.required[]", warnings):
        return
    if not isinstance(approval.get("role"), str) or not approval.get("role"):
        _append_schema_error(warnings, "approvals.required[].role is required and must be a string.")
    for key in approval:
        if key not in {"role", "condition"}:
            _append_schema_error(warnings, f"approvals.required[] additional property is not allowed: {key}")
    if "condition" in approval:
        condition = approval["condition"]
        if not _validate_object(condition, "approvals.required[].condition", warnings):
            return
        for field in {"field", "operator", "value"}:
            if field not in condition:
                _append_schema_error(warnings, f"approvals.required[].condition missing required field: {field}")
        for key in condition:
            if key not in {"field", "operator", "value"}:
                _append_schema_error(warnings, f"approvals.required[].condition additional property is not allowed: {key}")


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
