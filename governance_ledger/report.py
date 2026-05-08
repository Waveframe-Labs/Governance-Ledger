"""Review report convenience API."""

from __future__ import annotations

from typing import Any

from governance_ledger.extract import extract_constraints
from governance_ledger.review import build_review_report
from governance_ledger.validation import validate_authoring


def review_constraints(
    text: str,
    *,
    review_id: str | None = None,
    created_at: str | None = None,
    source_document: str | None = None,
    review_status: str = "pending",
) -> dict[str, Any]:
    """Extract policy text and return the human-reviewable detection report."""
    policy = extract_constraints(text)
    return build_review_report(
        text,
        policy,
        review_id=review_id,
        created_at=created_at,
        source_document=source_document,
        review_status=review_status,
    )


def validate_constraints(text: str) -> dict[str, Any]:
    """Return deterministic authoring warnings for governance policy text."""
    policy = extract_constraints(text)
    return validate_authoring(text, policy)
