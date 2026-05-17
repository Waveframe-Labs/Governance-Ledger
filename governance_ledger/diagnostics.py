from __future__ import annotations

from typing import Any


GOVERNANCE_DIAGNOSTIC_V1 = "governance_diagnostic.v1"

DIAGNOSTIC_DOMAINS = {
    "G1": "authority_threshold",
    "G3": "lifecycle",
    "G4": "artifact",
    "G5": "role_integrity",
    "G7": "governance_lint",
    "G8": "lineage",
}

DIAGNOSTIC_SEVERITIES = {"error", "warning", "info"}


def build_diagnostic(
    *,
    code: str,
    severity: str,
    title: str,
    detail: str,
    recommendation: str | None = None,
) -> dict[str, Any]:
    if severity not in DIAGNOSTIC_SEVERITIES:
        raise ValueError(f"unsupported diagnostic severity: {severity}")
    diagnostic = {
        "schema_version": GOVERNANCE_DIAGNOSTIC_V1,
        "type": "compiler_diagnostic",
        "severity": severity,
        "code": code,
        "domain": diagnostic_domain(code),
        "title": title,
        "detail": detail,
        "blocks_publication": severity == "error",
        "text": f"{severity.upper()} {code}: {title}. {detail}",
    }
    if recommendation:
        diagnostic["recommendation"] = recommendation
    validate_diagnostic(diagnostic)
    return diagnostic


def validate_diagnostic(diagnostic: Any) -> None:
    if not isinstance(diagnostic, dict):
        raise ValueError("diagnostic must be an object")
    if diagnostic.get("schema_version") != GOVERNANCE_DIAGNOSTIC_V1:
        raise ValueError("unsupported diagnostic schema_version")
    for field in ["type", "severity", "code", "domain", "title", "detail", "text"]:
        if not isinstance(diagnostic.get(field), str) or not diagnostic[field]:
            raise ValueError(f"diagnostic {field} must be a non-empty string")
    if diagnostic["type"] != "compiler_diagnostic":
        raise ValueError("diagnostic type must be compiler_diagnostic")
    if diagnostic["severity"] not in DIAGNOSTIC_SEVERITIES:
        raise ValueError("unsupported diagnostic severity")
    if not isinstance(diagnostic.get("blocks_publication"), bool):
        raise ValueError("diagnostic blocks_publication must be boolean")
    if diagnostic["blocks_publication"] != (diagnostic["severity"] == "error"):
        raise ValueError("diagnostic publication impact does not match severity")


def diagnostic_domain(code: str) -> str:
    return DIAGNOSTIC_DOMAINS.get(code[:2], "general")
