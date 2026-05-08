"""Create deterministic governance state snapshots."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from typing import Any

from governance_ledger.provenance import _utc_now


def create_snapshot(
    review: dict[str, Any],
    *,
    created_at: str | None = None,
) -> dict[str, Any]:
    """Freeze a governance review state with a deterministic snapshot hash."""
    frozen_review = deepcopy(review)
    snapshot_hash = _hash_snapshot_review(frozen_review)

    return {
        "snapshot_id": f"snapshot-{snapshot_hash[:12]}",
        "created_at": created_at or _utc_now(),
        "review_id": frozen_review.get("review_id"),
        "review_status": frozen_review.get("review_status"),
        "snapshot_hash": snapshot_hash,
        "review": frozen_review,
    }


def _hash_snapshot_review(review: dict[str, Any]) -> str:
    canonical_payload = json.dumps(
        review,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_payload).hexdigest()
