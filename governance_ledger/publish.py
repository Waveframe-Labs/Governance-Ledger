"""Operational approval and publish workflows for Governance-Ledger reviews."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance_ledger.contract_linkage import attach_compiled_contract
from governance_ledger.deployment import attach_deployment
from governance_ledger.lifecycle import transition_review_status
from governance_ledger.paths import artifact_path
from governance_ledger.provenance import _utc_now
from governance_ledger.registry import update_contract_registry
from governance_ledger.snapshot import create_snapshot
from governance_ledger.validation import has_validation_errors, validate_compiler_policy


def approve_review_file(
    review_path: str | Path,
    *,
    actor: str,
    timestamp: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Approve a pending or reviewed review artifact in place."""
    path = Path(review_path)
    review = _read_json(path)

    if review.get("review_status") == "pending":
        review = transition_review_status(
            review,
            "reviewed",
            actor=actor,
            timestamp=timestamp,
            note="Reviewed generated governance artifact.",
        )
    if review.get("review_status") == "reviewed":
        review = transition_review_status(
            review,
            "approved",
            actor=actor,
            timestamp=timestamp,
            note=note or "Approved governance artifact for publishing.",
        )
    elif review.get("review_status") != "approved":
        raise ValueError("Only pending, reviewed, or approved reviews can be approved.")

    approval_timestamp = review["lifecycle"][-1]["timestamp"]
    approval_note = review["lifecycle"][-1]["note"]
    review["approved_by"] = actor
    review["approved_at"] = approval_timestamp
    review["approval_note"] = approval_note

    _write_json(path, review)
    return review


def publish_review_file(
    review_path: str | Path,
    *,
    generated_dir: str | Path = "generated",
    contracts_dir: str | Path = "contracts",
    reviews_dir: str | Path = "reviews",
    snapshots_dir: str | Path = "snapshots",
    actor: str = "governance-team",
    compiler_actor: str = "compiler-service",
    deployed_by: str = "ops-team",
    environment: str = "production",
    runtime: str = "waveframe-guard",
    enforcement_engine_version: str = "0.12.0",
    timestamp: str | None = None,
) -> dict[str, str]:
    """Publish an approved review into contract, deployed review, and snapshot artifacts."""
    review_input_path = Path(review_path)
    review = _read_json(review_input_path)
    if review.get("review_status") != "approved":
        raise ValueError("Publishing requires review_status == 'approved'.")
    published_at = timestamp or _utc_now()

    policy_stem = _policy_stem_from_review_path(review_input_path)
    generated_path = Path(generated_dir) / f"{policy_stem}.generated.json"
    structured_policy = _read_json(generated_path)
    compiler_validation = validate_compiler_policy(structured_policy)
    if has_validation_errors(compiler_validation):
        raise ValueError(
            "Publishing requires generated policy to match the canonical compiler ingestion schema."
        )

    compiled_contract = _compile_policy(structured_policy)
    contract_path = Path(contracts_dir) / _contract_filename(compiled_contract)
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    _write_immutable_json(contract_path, compiled_contract)

    compiled_review = attach_compiled_contract(
        review,
        compiled_contract,
        actor=compiler_actor,
        timestamp=published_at,
    )
    deployed_review = attach_deployment(
        compiled_review,
        environment=environment,
        runtime=runtime,
        deployed_by=deployed_by,
        enforcement_engine_version=enforcement_engine_version,
        timestamp=published_at,
    )
    deployed_review["published_by"] = actor

    deployed_review_path = Path(reviews_dir) / f"{policy_stem}.deployed.review.json"
    deployed_review_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(deployed_review_path, deployed_review)

    snapshot = create_snapshot(deployed_review, created_at=published_at)
    snapshot_path = Path(snapshots_dir) / f"{snapshot['snapshot_id']}.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(snapshot_path, snapshot)

    manifest = _build_publication_manifest(
        compiled_contract,
        contract_path=contract_path,
        deployed_review_path=deployed_review_path,
        snapshot_path=snapshot_path,
        published_at=published_at,
        published_by=actor,
    )
    manifest_path = Path(contracts_dir) / f"{policy_stem}.publication_manifest.json"
    _write_immutable_json(manifest_path, manifest)
    update_contract_registry(
        contracts_dir,
        compiled_contract=compiled_contract,
        contract_path=contract_path,
        published_at=published_at,
        published_by=actor,
    )

    return {
        "contract": str(contract_path),
        "deployed_review": str(deployed_review_path),
        "manifest": str(manifest_path),
        "registry": str(Path(contracts_dir) / "index.json"),
        "snapshot": str(snapshot_path),
    }


def _compile_policy(policy: dict[str, Any]) -> dict[str, Any]:
    from compiler.compile_policy import compile_policy

    compiled_contract = compile_policy(policy)
    if not compiled_contract.get("contract_id") or not compiled_contract.get("contract_version"):
        raise ValueError("Canonical compiler output missing contract identity fields.")
    return compiled_contract


def _contract_filename(compiled_contract: dict[str, Any]) -> str:
    contract_id = compiled_contract["contract_id"]
    contract_version = compiled_contract["contract_version"]
    return f"{contract_id}-{contract_version}.contract.json"


def _build_publication_manifest(
    compiled_contract: dict[str, Any],
    *,
    contract_path: Path,
    deployed_review_path: Path,
    snapshot_path: Path,
    published_at: str,
    published_by: str,
) -> dict[str, Any]:
    contract_hash = compiled_contract["contract_hash"]
    if not contract_hash.startswith("sha256:"):
        contract_hash = f"sha256:{contract_hash}"
    return {
        "published_at": published_at,
        "published_by": published_by,
        "contracts": [
            {
                "contract_id": compiled_contract["contract_id"],
                "contract_version": compiled_contract["contract_version"],
                "contract_hash": contract_hash,
                "path": artifact_path(contract_path),
            }
        ],
        "reviews": [
            {
                "path": artifact_path(deployed_review_path),
            }
        ],
        "snapshots": [
            {
                "path": artifact_path(snapshot_path),
            }
        ],
    }


def _policy_stem_from_review_path(review_path: Path) -> str:
    name = review_path.name
    suffix = ".review.json"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return review_path.stem


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_immutable_json(path: Path, payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != serialized:
            raise ValueError(f"Refusing to overwrite immutable publication output: {path}")
        return
    path.write_text(serialized, encoding="utf-8")
