"""Deterministic extraction from policy prose into structured constraints."""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from governance_ledger.patterns import (
    ROLE_PATTERNS,
    SEPARATION_PATTERNS,
    THRESHOLD_PATTERNS,
)

DEFAULT_CONTRACT_ID = "finance-policy"
DEFAULT_CONTRACT_VERSION = "0.1.0"


def extract_constraints(text: str) -> dict[str, Any]:
    """Extract v0.1 governance constraints from policy text."""
    policy: dict[str, Any] = {
        "contract_id": DEFAULT_CONTRACT_ID,
        "contract_version": DEFAULT_CONTRACT_VERSION,
        "authority": {"required_roles": []},
        "approvals": {"thresholds": []},
    }

    normalized_text = _normalize_text(text)

    for pattern in ROLE_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            _append_unique(policy["authority"]["required_roles"], _normalize_role(match["role"]))

    if any(re.search(pattern, normalized_text, flags=re.IGNORECASE) for pattern in SEPARATION_PATTERNS):
        policy["authority"]["separation_of_duties"] = True

    for pattern in THRESHOLD_PATTERNS:
        for match in re.finditer(pattern, normalized_text, flags=re.IGNORECASE):
            requires_role = match.groupdict().get("requires_role")
            if requires_role:
                requires_role = _normalize_role(requires_role)
            elif policy["authority"]["required_roles"]:
                requires_role = policy["authority"]["required_roles"][0]
            else:
                requires_role = "manager"
            _append_unique_threshold(
                policy["approvals"]["thresholds"],
                {
                    "field": "amount",
                    "operator": ">",
                    "value": _parse_amount(
                        match["amount"],
                        match.groupdict().get("suffix"),
                    ),
                    "requires_role": requires_role,
                },
            )

    return _without_empty_sections(policy)


def _normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def _normalize_role(role: str) -> str:
    normalized = role.strip().lower().replace("-", "_")
    if normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def _parse_amount(amount: str, suffix: str | None = None) -> int:
    value = float(amount.replace(",", ""))
    if suffix and suffix.lower() in {"m", "million"}:
        value *= 1_000_000
    return int(value)


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _append_unique_threshold(thresholds: list[dict[str, Any]], threshold: dict[str, Any]) -> None:
    if threshold not in thresholds:
        thresholds.append(threshold)


def _without_empty_sections(policy: dict[str, Any]) -> dict[str, Any]:
    cleaned = deepcopy(policy)

    if (
        not cleaned["authority"].get("required_roles")
        and "separation_of_duties" not in cleaned["authority"]
    ):
        cleaned.pop("authority")
    elif not cleaned["authority"].get("required_roles"):
        cleaned["authority"].pop("required_roles")
    if not cleaned["approvals"]["thresholds"]:
        cleaned.pop("approvals")

    return cleaned
