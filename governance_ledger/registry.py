"""Published contract registry index for Governance-Ledger."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance_ledger.paths import artifact_path


def update_contract_registry(
    contracts_dir: str | Path,
    *,
    compiled_contract: dict[str, Any],
    contract_path: str | Path,
    published_at: str,
    published_by: str,
) -> dict[str, Any]:
    """Create or update contracts/index.json with a published contract entry."""
    contracts_root = Path(contracts_dir)
    contracts_root.mkdir(parents=True, exist_ok=True)
    index_path = contracts_root / "index.json"
    registry = _read_registry(index_path)
    entry = _registry_entry(
        compiled_contract,
        contract_path=contract_path,
        published_at=published_at,
        published_by=published_by,
    )

    contracts = [
        existing
        for existing in registry["contracts"]
        if not _same_contract(existing, entry)
    ]
    contracts.append(entry)
    registry["contracts"] = sorted(
        contracts,
        key=lambda item: (item["contract_id"], item["contract_version"], item["contract_hash"]),
    )
    _write_json(index_path, registry)
    return registry


def load_contract_registry(contracts_dir: str | Path = "contracts") -> dict[str, Any]:
    """Load contracts/index.json, returning an empty registry if absent."""
    return _read_registry(Path(contracts_dir) / "index.json")


def _registry_entry(
    compiled_contract: dict[str, Any],
    *,
    contract_path: str | Path,
    published_at: str,
    published_by: str,
) -> dict[str, str]:
    if not published_at:
        raise ValueError("Published contract registry entries require published_at.")
    contract_hash = compiled_contract["contract_hash"]
    if not contract_hash.startswith("sha256:"):
        contract_hash = f"sha256:{contract_hash}"
    return {
        "contract_id": compiled_contract["contract_id"],
        "contract_version": compiled_contract["contract_version"],
        "contract_hash": contract_hash,
        "path": artifact_path(contract_path),
        "published_at": published_at,
        "published_by": published_by,
    }


def _same_contract(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return (
        left.get("contract_id") == right.get("contract_id")
        and left.get("contract_version") == right.get("contract_version")
    )


def _read_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"contracts": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
