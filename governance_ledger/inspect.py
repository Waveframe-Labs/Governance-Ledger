"""Operator inspection helpers for Governance-Ledger artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance_ledger.paths import artifact_path
from governance_ledger.registry import load_contract_registry


def list_contracts(contracts_dir: str | Path = "contracts") -> dict[str, Any]:
    """Return published contracts from the registry index."""
    return load_contract_registry(contracts_dir)


def format_contract_list(registry: dict[str, Any]) -> str:
    """Format published contract registry entries for operators."""
    lines = ["Published Contracts"]
    contracts = registry.get("contracts", [])
    if not contracts:
        lines.extend(["", "none"])
        return "\n".join(lines)

    for contract in contracts:
        lines.extend(
            [
                "",
                f"{contract['contract_id']} v{contract['contract_version']}",
                f"hash: {contract['contract_hash']}",
                f"published_at: {contract.get('published_at')}",
                f"path: {contract['path']}",
            ]
        )
    return "\n".join(lines)


def show_artifact(path: str | Path) -> dict[str, Any]:
    """Load a JSON artifact for inspection."""
    artifact_path = Path(path)
    return json.loads(artifact_path.read_text(encoding="utf-8"))


def format_artifact(path: str | Path, artifact: dict[str, Any]) -> str:
    """Format a JSON artifact for readable CLI inspection."""
    return "\n".join(
        [
            "[Governance Ledger]",
            "",
            f"Artifact: {artifact_path(path)}",
            "",
            json.dumps(artifact, indent=2, sort_keys=True),
        ]
    )
