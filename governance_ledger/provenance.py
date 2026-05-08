"""Stable provenance metadata for governance review artifacts."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from governance_ledger.extract import _normalize_text

DEFAULT_REVIEW_STATUS = "pending"


def build_review_provenance(
    text: str,
    *,
    review_id: str | None = None,
    created_at: str | None = None,
    source_document: str | None = None,
    review_status: str = DEFAULT_REVIEW_STATUS,
) -> dict[str, str | None]:
    """Build explicit provenance metadata for a review artifact."""
    return {
        "review_id": review_id or _stable_review_id(text),
        "created_at": created_at or _utc_now(),
        "source_document": source_document,
        "review_status": review_status,
    }


def _stable_review_id(text: str) -> str:
    digest = hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()
    return f"review-{digest[:12]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
