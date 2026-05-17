from __future__ import annotations

import hashlib
import json
from typing import Any


GOVERNANCE_NORMALIZATION_REPORT_V1 = "governance_normalization_report.v1"
GOVERNANCE_COMPILATION_REPORT_V1 = "governance_compilation_report.v1"


def build_compilation_report(
    *,
    policy: dict[str, Any],
    source_governance: dict[str, Any] | None = None,
    normalized_statements: list[dict[str, Any]],
    coverage: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    publication_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    authority_ref = _authority_ref(policy)
    report = {
        "schema_version": GOVERNANCE_COMPILATION_REPORT_V1,
        "authority_ref": authority_ref,
        "source_governance": source_governance,
        "source_hash": (source_governance or {}).get("source_hash"),
        "coverage": coverage,
        "normalized_statements": normalized_statements,
        "statement_traces": [
            _statement_trace(statement, diagnostics)
            for statement in normalized_statements
        ],
        "diagnostics": diagnostics,
        "diagnostic_summary": _diagnostic_summary(diagnostics),
        "semantic_observations": [
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.get("severity") in {"info", "warning"}
        ],
        "lint_results": [
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.get("domain") == "governance_lint"
        ],
        "publication_gate": publication_gate,
        "compiler_summary": _compiler_summary(policy, normalized_statements, coverage, diagnostics),
    }
    report["report_hash"] = _report_hash(report)
    return report


def build_normalization_report(
    *,
    normalized_statements: list[dict[str, Any]],
    coverage: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    publication_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = {
        "schema_version": GOVERNANCE_NORMALIZATION_REPORT_V1,
        "statement_traces": [
            _statement_trace(statement, diagnostics)
            for statement in normalized_statements
        ],
        "coverage": coverage,
        "diagnostics": diagnostics,
        "diagnostic_summary": _diagnostic_summary(diagnostics),
        "publication_gate": publication_gate,
        "semantic_observations": [
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.get("severity") in {"info", "warning"}
        ],
        "lint_results": [
            diagnostic
            for diagnostic in diagnostics
            if diagnostic.get("domain") == "governance_lint"
        ],
    }
    return report


def _authority_ref(policy: dict[str, Any]) -> str:
    contract_id = policy.get("contract_id")
    contract_version = policy.get("contract_version")
    if not contract_id or not contract_version:
        return "unknown@unknown"
    return f"{contract_id}@{contract_version}"


def _compiler_summary(
    policy: dict[str, Any],
    normalized_statements: list[dict[str, Any]],
    coverage: dict[str, Any],
    diagnostics: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "contract_id": policy.get("contract_id"),
        "contract_version": policy.get("contract_version"),
        "statement_count": len(normalized_statements),
        "normalized_statement_count": coverage.get("deterministically_normalized"),
        "diagnostic_count": len(diagnostics),
        "blocking_diagnostic_count": sum(
            1 for diagnostic in diagnostics if diagnostic.get("blocks_publication") is True
        ),
        "coverage_percent": coverage.get("coverage_percent"),
        "required_roles": policy.get("authority", {}).get("required_roles", []),
        "required_approval_count": len(policy.get("approvals", {}).get("required", [])),
        "artifact_count": len(policy.get("artifacts", {}).get("required", [])),
        "stage_transition_count": len(policy.get("stages", {}).get("allowed_transitions", [])),
    }


def _report_hash(report: dict[str, Any]) -> str:
    canonical = {
        key: value
        for key, value in report.items()
        if key != "report_hash"
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(serialized.encode('utf-8')).hexdigest()}"


def _statement_trace(statement: dict[str, Any], diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    attributed = _diagnostics_for_statement(statement.get("text", ""), diagnostics)
    return {
        "statement": statement.get("text"),
        "classification": statement.get("classification"),
        "normalized": statement.get("normalized", []),
        "normalized_statement": statement.get("normalized_statement", False),
        "diagnostics": attributed,
    }


def _diagnostics_for_statement(statement_text: str, diagnostics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not statement_text:
        return []
    statement_lower = statement_text.lower()
    matches = []
    for diagnostic in diagnostics:
        haystack = " ".join(
            str(diagnostic.get(field, ""))
            for field in ["title", "detail", "text"]
        ).lower()
        if any(token in haystack for token in _meaningful_tokens(statement_lower)):
            matches.append(diagnostic)
    return matches


def _meaningful_tokens(text: str) -> list[str]:
    return [
        token.strip(".,:;()[]\"'")
        for token in text.split()
        if len(token.strip(".,:;()[]\"'")) >= 5
    ]


def _diagnostic_summary(diagnostics: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "error": sum(1 for item in diagnostics if item.get("severity") == "error"),
        "warning": sum(1 for item in diagnostics if item.get("severity") == "warning"),
        "info": sum(1 for item in diagnostics if item.get("severity") == "info"),
    }
