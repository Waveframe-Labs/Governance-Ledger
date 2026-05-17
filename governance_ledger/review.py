"""Build inspectable review artifacts for extracted governance constraints."""

from __future__ import annotations

from typing import Any

from governance_ledger.statement_normalizer import (
    normalize_governance_statements,
)
from governance_ledger.normalization_report import (
    build_compilation_report,
    build_normalization_report,
)
from governance_ledger.provenance import build_review_provenance
from governance_ledger.validation import validate_authoring


def build_review_report(
    text: str,
    policy: dict[str, Any],
    *,
    review_id: str | None = None,
    created_at: str | None = None,
    source_document: str | None = None,
    review_status: str = "pending",
) -> dict[str, Any]:
    """Explain which governance constraints were detected from source text."""
    detected_constraints: list[dict[str, Any]] = []
    normalized_statements = normalize_governance_statements(text)
    for statement in normalized_statements:
        for item in statement["normalized"]:
            _append_unique_constraint(detected_constraints, item)

    validation_report = validate_authoring(text, policy)
    diagnostics = [
        warning
        for warning in validation_report["warnings"]
        if warning.get("type") == "compiler_diagnostic"
    ]

    provenance = build_review_provenance(
        text,
        review_id=review_id,
        created_at=created_at,
        source_document=source_document,
        review_status=review_status,
    )

    compilation_report = build_compilation_report(
        policy=policy,
        source_governance=provenance["source_governance"],
        normalized_statements=normalized_statements,
        coverage=validation_report["coverage"],
        diagnostics=diagnostics,
    )
    normalization_report = build_normalization_report(
        normalized_statements=normalized_statements,
        coverage=validation_report["coverage"],
        diagnostics=diagnostics,
    )

    return {
        **provenance,
        "detected_constraints": detected_constraints,
        "normalized_statements": normalized_statements,
        "warnings": validation_report["warnings"],
        "extraction_coverage": validation_report["coverage"],
        "compilation_report": compilation_report,
        "normalization_report": normalization_report,
    }


def _append_unique_constraint(
    detected_constraints: list[dict[str, Any]],
    constraint: dict[str, Any],
) -> None:
    if constraint not in detected_constraints:
        detected_constraints.append(constraint)
