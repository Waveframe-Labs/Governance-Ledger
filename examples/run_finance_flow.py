"""Run the canonical Governance-Ledger finance lifecycle walkthrough."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from governance_ledger import (  # noqa: E402
    attach_compiled_contract,
    attach_deployment,
    create_snapshot,
    diff_reviews,
    extract_constraints,
    review_constraints,
    rollback_to_snapshot,
    transition_review_status,
    validate_constraints,
)

EXAMPLE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = EXAMPLE_DIR / "artifacts"
POLICY_PATH = EXAMPLE_DIR / "finance_governance.txt"


def main() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

    policy_text = POLICY_PATH.read_text(encoding="utf-8")

    structured_policy = extract_constraints(policy_text)
    _write_json("structured_policy.json", structured_policy)

    review = review_constraints(
        policy_text,
        review_id="review-finance-001",
        created_at="2026-05-07T20:00:00Z",
        source_document=POLICY_PATH.name,
    )
    _write_json("review.json", review)

    validation = validate_constraints(policy_text)
    _write_json("validation.json", validation)

    reviewed = transition_review_status(
        review,
        "reviewed",
        actor="governance-team",
        timestamp="2026-05-07T20:10:00Z",
        note="Reviewed extracted finance governance constraints.",
    )
    approved = transition_review_status(
        reviewed,
        "approved",
        actor="governance-team",
        timestamp="2026-05-07T20:20:00Z",
        note="Approved for deterministic compilation.",
    )
    _write_json("approved_review.json", approved)

    compiled_contract = _compile_policy(structured_policy)
    _write_json("compiled_contract.json", compiled_contract)

    compiled_review = attach_compiled_contract(
        approved,
        compiled_contract,
        actor="compiler-service",
        timestamp="2026-05-07T20:30:00Z",
    )
    _write_json("compiled_review.json", compiled_review)

    deployed_review = attach_deployment(
        compiled_review,
        environment="production",
        runtime="waveframe-guard",
        deployed_by="ops-team",
        enforcement_engine_version="0.12.0",
        timestamp="2026-05-07T21:00:00Z",
    )
    _write_json("deployed_review.json", deployed_review)

    snapshot = create_snapshot(
        deployed_review,
        created_at="2026-05-07T21:30:00Z",
    )
    _write_json("snapshot.json", snapshot)

    updated_runtime_review = deepcopy(deployed_review)
    updated_runtime_review["deployment"]["engine_version"] = "0.13.0"
    updated_runtime_review["deployment"]["deployed_at"] = "2026-05-07T22:00:00Z"

    review_diff = diff_reviews(deployed_review, updated_runtime_review)
    _write_json("diff.json", review_diff)

    rollback = rollback_to_snapshot(
        updated_runtime_review,
        snapshot,
        actor="ops-team",
        timestamp="2026-05-07T22:15:00Z",
        note="restore deployed finance governance snapshot",
    )
    _write_json("rollback.json", rollback)

    print(f"Wrote Governance-Ledger finance artifacts to {ARTIFACT_DIR}")


def _compile_policy(policy: dict[str, Any]) -> dict[str, Any]:
    try:
        from compiler.compile_policy import compile_policy
    except ImportError:
        return _example_compile_policy(policy, compiler_note="canonical compiler unavailable")

    try:
        return compile_policy(policy)
    except Exception as exc:
        return _example_compile_policy(
            policy,
            compiler_note=f"canonical compiler rejected v0.1 example policy: {exc}",
        )


def _example_compile_policy(
    policy: dict[str, Any],
    *,
    compiler_note: str,
) -> dict[str, Any]:
    compiled_contract = {
        "contract_id": policy.get("contract_id", "finance-policy"),
        "contract_version": policy.get("contract_version", "0.1.0"),
        "schema_version": "example-compiled-contract/v0.1",
        "compiler": "governance-ledger-example",
        "compiler_note": compiler_note,
        "authority": policy.get("authority", {}),
        "approvals": policy.get("approvals", {}),
        "invariants": policy.get("invariants", {}),
    }
    compiled_contract["contract_hash"] = _canonical_hash(compiled_contract)
    return compiled_contract


def _canonical_hash(payload: dict[str, Any]) -> str:
    canonical_payload = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical_payload).hexdigest()


def _write_json(filename: str, payload: dict[str, Any]) -> None:
    (ARTIFACT_DIR / filename).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
