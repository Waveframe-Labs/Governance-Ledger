"""Deterministic extraction from policy prose into structured constraints."""

from __future__ import annotations

from typing import Any

from governance_ledger.statement_normalizer import (
    normalize_operator,
    normalize_policy_text,
    normalize_role,
    normalize_text,
    parse_amount,
)

DEFAULT_CONTRACT_ID = "finance-policy"
DEFAULT_CONTRACT_VERSION = "0.1.0"


def extract_constraints(text: str) -> dict[str, Any]:
    """Extract v0.1 governance constraints from policy text."""
    return normalize_policy_text(text)


def _normalize_text(text: str) -> str:
    return normalize_text(text)


def _normalize_role(role: str) -> str:
    return normalize_role(role)


def _parse_amount(amount: str, suffix: str | None = None) -> int:
    return parse_amount(amount, suffix)


def _normalize_operator(phrase: str) -> str:
    return normalize_operator(phrase)
