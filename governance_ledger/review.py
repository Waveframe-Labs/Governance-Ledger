"""Build inspectable review artifacts for extracted governance constraints."""

from __future__ import annotations

import re
from typing import Any

from governance_ledger.extract import _normalize_role, _normalize_text, _parse_amount
from governance_ledger.patterns import (
    ROLE_PATTERNS,
    SEPARATION_PATTERNS,
    THRESHOLD_PATTERNS,
)
from governance_ledger.provenance import build_review_provenance
from governance_ledger.validation import validate_authoring


def build_review_report(
    text: str,
    policy: dict[str, Any],
    *,
    review_id: str | None = None,
    created_at: str | None = None,
    source_document: str | None = None,
    review_status: str = "pending",
) -> dict[str, Any]:
    """Explain which governance constraints were detected from source text."""
    normalized_text = _normalize_text(text)
    detected_constraints: list[dict[str, Any]] = []

    for pattern in ROLE_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            role = _normalize_role(match["role"])
            if role in policy.get("authority", {}).get("required_roles", []):
                _append_unique_constraint(
                    detected_constraints,
                    {
                        "type": "required_role",
                        "value": role,
                        "source_text": match.group(0),
                    },
                )

    for pattern in SEPARATION_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            if policy.get("authority", {}).get("separation_of_duties") is True:
                _append_unique_constraint(
                    detected_constraints,
                    {
                        "type": "separation_of_duties",
                        "value": True,
                        "source_text": match.group(0),
                    },
                )

    for pattern in THRESHOLD_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            threshold = _parse_amount(match["amount"], match.groupdict().get("suffix"))
            extracted_threshold = _matching_threshold(policy, threshold)
            if extracted_threshold:
                _append_unique_constraint(
                    detected_constraints,
                    {
                        "type": "approval_threshold",
                        "field": extracted_threshold["field"],
                        "operator": extracted_threshold["operator"],
                        "value": threshold,
                        "requires_role": extracted_threshold["requires_role"],
                        "source_text": match.groupdict().get("source", match.group(0)),
                    },
                )

    validation_report = validate_authoring(text, policy)

    return {
        **build_review_provenance(
            text,
            review_id=review_id,
            created_at=created_at,
            source_document=source_document,
            review_status=review_status,
        ),
        "detected_constraints": detected_constraints,
        "warnings": validation_report["warnings"],
    }


def _append_unique_constraint(
    detected_constraints: list[dict[str, Any]],
    constraint: dict[str, Any],
) -> None:
    if constraint not in detected_constraints:
        detected_constraints.append(constraint)


def _matching_threshold(policy: dict[str, Any], value: Any) -> dict[str, Any] | None:
    for threshold in policy.get("approvals", {}).get("thresholds", []):
        if (
            threshold.get("field") == "amount"
            and threshold.get("operator") == ">"
            and threshold.get("value") == value
        ):
            return threshold
    return None
