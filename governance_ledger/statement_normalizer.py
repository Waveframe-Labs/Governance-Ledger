"""Deterministic governance statement classification and normalization."""

from __future__ import annotations

import re
from typing import Any


OPERATOR_MAP = {
    "above": ">",
    "over": ">",
    "greater than": ">",
    "exceeding": ">",
    "at least": ">=",
    "up to": "<=",
    "below": "<",
    "under": "<",
    "less than": "<",
}

GOVERNANCE_SIGNAL_PATTERN = (
    r"\b(approval|approve|authority|must|only|require|requires|required|shall|should|"
    r"transfer|transfers|purchase|purchases|payment|payments|invoice|invoices|access|deploy|"
    r"deployment|patient|records?|risk|reviewer|audit|log|logged|recorded|retained|blocked|"
    r"reported|compliance|review|reviewed|submitted|approved|rejected|executed)\b"
)


def normalize_policy_text(text: str) -> dict[str, Any]:
    policy: dict[str, Any] = {
        "contract_id": "finance-policy",
        "contract_version": "0.1.0",
        "authority": {"required_roles": []},
        "approvals": {"required": [], "thresholds": []},
        "artifacts": {"required": []},
    }
    statements = normalize_governance_statements(text)
    for statement in statements:
        for item in statement["normalized"]:
            _apply_normalized_item(policy, item)
    return _without_empty_sections(policy)


def normalize_governance_statements(text: str) -> list[dict[str, Any]]:
    normalized_text = normalize_text(text)
    statements = []
    for statement in split_governance_statements(normalized_text):
        classification = classify_statement(statement["text"])
        normalized = _normalize_statement(statement["text"], classification)
        statements.append(
            {
                **statement,
                "classification": classification,
                "normalized": normalized,
                "normalized_statement": bool(normalized),
            }
        )
    return statements


def split_governance_statements(text: str) -> list[dict[str, Any]]:
    statements: list[dict[str, Any]] = []
    for match in re.finditer(r"[^.!?]+[.!?]?", text):
        raw = match.group(0).strip()
        if not raw:
            continue
        statement = re.sub(r"^\d+\.\s*", "", raw).strip()
        statement = re.sub(r"\s+\d+\.$", "", statement).strip()
        if not statement or not re.search(GOVERNANCE_SIGNAL_PATTERN, statement, flags=re.IGNORECASE):
            continue
        if re.fullmatch(r".*\bpolicy\b", statement, flags=re.IGNORECASE) and not re.search(
            r"\b(must|only|require|requires|required|shall|should|may)\b",
            statement,
            flags=re.IGNORECASE,
        ):
            continue
        statements.append({"text": statement, "span": match.span()})
    return statements


def classify_statement(statement: str) -> str:
    if _threshold_match(statement):
        return "conditional_threshold_approval"
    if _approval_authority_match(statement):
        return "approval_authority_constraint"
    if _role_authority_match(statement):
        return "role_authority_constraint"
    if _separation_match(statement):
        return "separation_of_duties_constraint"
    if _lifecycle_match(statement):
        return "lifecycle_transition_constraint"
    if re.search(r"\bunauthorized\b.*?\b(?:attempts?|access|transfer|payment)s?\b.*?\b(?:blocked|reported)\b", statement, flags=re.IGNORECASE):
        return "unauthorized_attempt_reporting_requirement"
    if _artifact_match(statement):
        return "artifact_requirement"
    return "unclassified_governance_statement"


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def normalize_role(role: str) -> str:
    normalized = role.strip().lower().replace("-", "_")
    if normalized.endswith("s") and not normalized.endswith("ss"):
        return normalized[:-1]
    return normalized


def parse_amount(amount: str, suffix: str | None = None) -> int:
    value = float(amount.replace(",", ""))
    normalized_suffix = (suffix or "").lower()
    if normalized_suffix in {"k", "thousand"}:
        value *= 1_000
    elif normalized_suffix in {"m", "million"}:
        value *= 1_000_000
    return int(value)


def normalize_operator(phrase: str) -> str:
    normalized = " ".join(phrase.lower().split())
    return OPERATOR_MAP[normalized]


def _normalize_statement(statement: str, classification: str) -> list[dict[str, Any]]:
    if classification == "conditional_threshold_approval":
        match = _threshold_match(statement)
        if not match:
            return []
        role = match.groupdict().get("requires_role") or match.groupdict().get("requires_role_alt")
        if not role:
            return []
        condition = {
            "field": "amount",
            "operator": normalize_operator(match["operator_phrase"]),
            "value": parse_amount(match["amount"], match.groupdict().get("suffix")),
        }
        normalized = [
            {
                "type": "required_role",
                "value": normalize_role(role),
                "source_text": statement,
            },
            {
                "type": "approval_threshold",
                "field": "amount",
                "operator": condition["operator"],
                "value": condition["value"],
                "requires_role": normalize_role(role),
                "source_text": match.groupdict().get("source", statement),
            },
            {
                "type": "required_approval",
                "role": normalize_role(role),
                "condition": condition,
                "source_text": statement,
            },
        ]
        return normalized
    if classification == "approval_authority_constraint":
        match = _approval_authority_match(statement)
        if not match:
            return []
        return [
            {
                "type": "required_role",
                "value": normalize_role(match["role"]),
                "source_text": statement,
            },
            {
                "type": "required_approval",
                "role": normalize_role(match["role"]),
                "source_text": statement,
            }
        ]
    if classification == "role_authority_constraint":
        match = _role_authority_match(statement)
        if not match:
            return []
        return [
            {
                "type": "required_role",
                "value": normalize_role(match["role"]),
                "source_text": statement,
            }
        ]
    if classification == "separation_of_duties_constraint":
        return [
            {
                "type": "separation_of_duties",
                "value": True,
                "source_text": statement,
            }
        ]
    if classification == "lifecycle_transition_constraint":
        match = _lifecycle_match(statement)
        if not match:
            return []
        return [
            {
                "type": "allowed_transition",
                "from": normalize_stage(match["from"]),
                "to": normalize_stage(match["to"]),
                "source_text": statement,
            }
        ]
    if classification == "artifact_requirement":
        artifact = _artifact_value(statement)
        if not artifact:
            return []
        return [
            {
                "type": "required_artifact",
                "value": artifact,
                "source_text": statement,
            }
        ]
    if classification == "unauthorized_attempt_reporting_requirement":
        return [
            {
                "type": "required_artifact",
                "value": "compliance_report",
                "source_text": statement,
            }
        ]
    return []


def _threshold_match(statement: str) -> re.Match[str] | None:
    amount = r"\$?(?P<amount>\d[\d,]*(?:\.\d+)?)\s*(?P<suffix>k|m|thousand|million)?"
    operator = r"(?P<operator_phrase>above|over|greater\s+than|exceeding|at\s+least|up\s+to|below|under|less\s+than)"
    subject = r"(?:transfers?|purchases?|payments?|invoices?|requests?)"
    patterns = [
        rf"\b(?:any\s+)?{subject}\s+(?P<source>{operator}\s+{amount})\b.*?\bapproval\s+from\s+(?:(?:a|an|the)\s+)?(?P<requires_role>[a-z][a-z_-]*)\b",
        rf"\b(?:any\s+)?{subject}\s+(?P<source>{operator}\s+{amount})\b.*?\brequires?\s+(?P<requires_role_alt>[a-z][a-z_-]*)\s+approval\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, statement, flags=re.IGNORECASE)
        if match:
            return match
    return None


def _approval_authority_match(statement: str) -> re.Match[str] | None:
    patterns = [
        r"\bonly\s+employees?\s+with\s+(?:the\s+)?(?P<role>[a-z][a-z_-]*)\s+role\s+may\s+approve\b",
        r"\bonly\s+(?P<role>[a-z][a-z_-]*)\s+may\s+approve\b",
        r"\brequires?\s+(?P<role>[a-z][a-z_-]*)\s+approval\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, statement, flags=re.IGNORECASE)
        if match:
            return match
    return None


def _role_authority_match(statement: str) -> re.Match[str] | None:
    patterns = [
        r"\bonly\s+users?\s+with\s+(?:the\s+)?(?P<role>[a-z][a-z_-]*)\s+role\s+may\s+(?:access|execute|deploy)\b",
        r"\bonly\s+(?P<role>[a-z][a-z_-]*)s?\s+may\s+(?:access|execute|deploy)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, statement, flags=re.IGNORECASE)
        if match:
            return match
    return None


def _separation_match(statement: str) -> re.Match[str] | None:
    return re.search(
        r"\b(?:must\s+be\s+(?:separate|different)|must\s+not\s+be\s+the\s+same|separation\s+of\s+duties|"
        r"(?:creates?|creates\s+a\s+transfer\s+request).*?"
        r"(?:may\s+not|must\s+not|cannot)\s+be\s+the\s+same.*?approves?)\b",
        statement,
        flags=re.IGNORECASE,
    )


def _lifecycle_match(statement: str) -> re.Match[str] | None:
    return re.search(
        r"\b(?:move|transition|advance)s?\s+from\s+(?P<from>[a-z][a-z_-]*)\s+to\s+(?P<to>[a-z][a-z_-]*)\b",
        statement,
        flags=re.IGNORECASE,
    )


def _artifact_match(statement: str) -> bool:
    return bool(
        re.search(
            r"\b(?:approval|approvals|access decisions?|decisions?|evidence|attempts?|requests?)\b.*?"
            r"\b(?:recorded|logged|retained|reported)\b",
            statement,
            flags=re.IGNORECASE,
        )
        or re.search(r"\baudit\s+log\b", statement, flags=re.IGNORECASE)
    )


def _artifact_value(statement: str) -> str | None:
    lowered = statement.lower()
    if "compliance" in lowered or "reported" in lowered:
        return "compliance_report"
    if "access" in lowered:
        return "access_audit_record"
    if "approval" in lowered:
        return "approval_audit_record"
    if "evidence" in lowered or "retained" in lowered:
        return "evidence_record"
    if "audit" in lowered or "logged" in lowered or "recorded" in lowered:
        return "audit_record"
    return None


def normalize_stage(stage: str) -> str:
    return stage.strip().lower().replace("-", "_")


def _apply_normalized_item(policy: dict[str, Any], item: dict[str, Any]) -> None:
    if item["type"] == "required_role":
        _append_unique(policy["authority"]["required_roles"], item["value"])
    elif item["type"] == "approval_threshold":
        _append_unique_threshold(
            policy["approvals"]["thresholds"],
            {
                "field": item["field"],
                "operator": item["operator"],
                "value": item["value"],
                "requires_role": item["requires_role"],
            },
        )
    elif item["type"] == "required_approval":
        approval = {"role": item["role"]}
        if "condition" in item:
            approval["condition"] = item["condition"]
        _append_unique_approval(policy["approvals"]["required"], approval)
    elif item["type"] == "separation_of_duties":
        policy["authority"]["separation_of_duties"] = True
    elif item["type"] == "required_artifact":
        _append_unique(policy["artifacts"]["required"], item["value"])
    elif item["type"] == "allowed_transition":
        policy.setdefault("stages", {}).setdefault("allowed_transitions", [])
        _append_unique_transition(
            policy["stages"]["allowed_transitions"],
            {
                "from": item["from"],
                "to": item["to"],
            },
        )


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _append_unique_threshold(thresholds: list[dict[str, Any]], threshold: dict[str, Any]) -> None:
    if threshold not in thresholds:
        thresholds.append(threshold)


def _append_unique_approval(approvals: list[dict[str, Any]], approval: dict[str, Any]) -> None:
    if approval not in approvals:
        approvals.append(approval)


def _append_unique_transition(transitions: list[dict[str, str]], transition: dict[str, str]) -> None:
    if transition not in transitions:
        transitions.append(transition)


def _without_empty_sections(policy: dict[str, Any]) -> dict[str, Any]:
    cleaned = {
        key: value.copy() if isinstance(value, dict) else value
        for key, value in policy.items()
    }
    if (
        not cleaned["authority"].get("required_roles")
        and "separation_of_duties" not in cleaned["authority"]
    ):
        cleaned.pop("authority")
    elif not cleaned["authority"].get("required_roles"):
        cleaned["authority"].pop("required_roles")
    if not cleaned["approvals"].get("thresholds"):
        cleaned["approvals"].pop("thresholds", None)
    if not cleaned["approvals"].get("required"):
        cleaned["approvals"].pop("required", None)
    if not cleaned["approvals"]:
        cleaned.pop("approvals")
    if not cleaned["artifacts"]["required"]:
        cleaned.pop("artifacts")
    if "stages" in cleaned and not cleaned["stages"].get("allowed_transitions"):
        cleaned.pop("stages")
    return cleaned
