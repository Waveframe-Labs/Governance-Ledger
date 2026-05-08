"""Restore governance review state from validated snapshots with rollback provenance."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from governance_ledger.provenance import _utc_now
from governance_ledger.snapshot import _hash_snapshot_review


def rollback_to_snapshot(
    current_review: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    actor: str,
    timestamp: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Return a restored review state with rollback provenance appended."""
    _validate_snapshot(snapshot)

    restored_review = deepcopy(snapshot["review"])
    restored_review.setdefault("lifecycle", []).append(
        {
            "from_snapshot": snapshot["snapshot_id"],
            "rollback_actor": actor,
            "rollback_reason": note,
            "rolled_back_at": timestamp or _utc_now(),
        }
    )
    restored_review["rollback"] = {
        "from_review_id": current_review.get("review_id"),
        "from_review_status": current_review.get("review_status"),
        "to_snapshot_id": snapshot["snapshot_id"],
        "to_review_id": snapshot.get("review_id"),
        "to_review_status": snapshot.get("review_status"),
        "rollback_actor": actor,
        "rollback_reason": note,
        "rolled_back_at": restored_review["lifecycle"][-1]["rolled_back_at"],
    }

    return restored_review


def _validate_snapshot(snapshot: dict[str, Any]) -> None:
    review = snapshot.get("review")
    if not isinstance(review, dict):
        raise ValueError("Snapshot missing review state.")

    snapshot_hash = snapshot.get("snapshot_hash")
    if not snapshot_hash:
        raise ValueError("Snapshot missing snapshot_hash.")

    expected_hash = _hash_snapshot_review(review)
    if snapshot_hash != expected_hash:
        raise ValueError("Snapshot integrity validation failed.")

    snapshot_id = snapshot.get("snapshot_id")
    expected_snapshot_id = f"snapshot-{expected_hash[:12]}"
    if snapshot_id != expected_snapshot_id:
        raise ValueError("Snapshot ID does not match snapshot hash.")
