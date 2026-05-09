"""Operational checks for Governance-Ledger generated artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def check_validation_directory(generated_dir: str | Path) -> dict[str, Any]:
    """Return validation check results and error-severity warnings."""
    generated_root = Path(generated_dir)
    errors: list[dict[str, str]] = []
    warning_count = 0
    policy_count = 0

    for path in sorted(generated_root.glob("*.validation.json")):
        policy_count += 1
        validation = json.loads(path.read_text(encoding="utf-8"))
        for warning in validation.get("warnings", []):
            warning_count += 1
            if warning.get("severity") == "error":
                errors.append(
                    {
                        "file": str(path),
                        "type": warning.get("type", ""),
                        "text": warning.get("text", ""),
                    }
                )

    return {
        "status": "failed" if errors else "passed",
        "publication_status": "BLOCKED_ERRORS" if errors else "READY_FOR_REVIEW",
        "policy_count": policy_count,
        "warning_count": warning_count,
        "error_count": len(errors),
        "errors": errors,
    }


def format_check_summary(result: dict[str, Any]) -> str:
    """Format validation check results for CLI output."""
    lines = [
        "[Governance Ledger]",
        "",
        "Governance Validation Summary",
        "",
        f"Policies Processed: {result['policy_count']}",
        f"Warnings: {result['warning_count']}",
        f"Errors: {result['error_count']}",
        "",
        "Publication Status:",
        f"  {result['publication_status']}",
    ]
    for error in result["errors"]:
        lines.extend(
            [
                "",
                f"File: {error['file']}",
                f"  {error['type']}: {error['text']}",
            ]
        )
    return "\n".join(lines)
