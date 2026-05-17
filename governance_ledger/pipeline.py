"""File-based policy authoring pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from governance_ledger.extract import extract_constraints
from governance_ledger.integration_paths import ensure_integration_paths
from governance_ledger.review import build_review_report
from governance_ledger.validation import has_validation_errors, validate_compiler_policy


def build_contract_files(
    policy_path: str | Path,
    structured_policy_path: str | Path,
    compiled_contract_path: str | Path,
    review_report_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run policy.txt -> structured_policy.json -> compiled_contract.json."""
    policy_input_path = Path(policy_path)
    policy_text = policy_input_path.read_text(encoding="utf-8")
    structured_policy = extract_constraints(policy_text)
    compiler_validation = validate_compiler_policy(structured_policy)
    if has_validation_errors(compiler_validation):
        raise ValueError(
            "Compiling requires extracted policy to match the canonical compiler ingestion schema."
        )
    review_report = build_review_report(
        policy_text,
        structured_policy,
        source_document=policy_input_path.name,
    )
    ensure_integration_paths(compiler=True)
    from compiler.compile_policy import compile_policy

    compiled_contract = compile_policy(structured_policy)

    _write_json(structured_policy_path, structured_policy)
    if review_report_path is not None:
        _write_json(review_report_path, review_report)
    _write_json(compiled_contract_path, compiled_contract)

    return compiled_contract


def _write_json(path: str | Path, payload: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
