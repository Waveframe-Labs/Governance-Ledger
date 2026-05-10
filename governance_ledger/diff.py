"""Deterministic comparison for governance review artifacts."""

from __future__ import annotations

from typing import Any


def diff_reviews(old_review: dict[str, Any], new_review: dict[str, Any]) -> dict[str, Any]:
    """Return structured differences between two governance review artifacts."""
    added_constraints, removed_constraints, modified_constraints = _diff_constraints(
        old_review.get("detected_constraints", []),
        new_review.get("detected_constraints", []),
    )

    return {
        "added_constraints": added_constraints,
        "removed_constraints": removed_constraints,
        "modified_constraints": modified_constraints,
        "new_warnings": _added_items(
            old_review.get("warnings", []),
            new_review.get("warnings", []),
        ),
        "resolved_warnings": _removed_items(
            old_review.get("warnings", []),
            new_review.get("warnings", []),
        ),
        "deployment_changes": _deployment_changes(
            old_review.get("deployment"),
            new_review.get("deployment"),
        ),
    }


def _diff_constraints(
    old_constraints: list[dict[str, Any]],
    new_constraints: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    old_by_key = {_constraint_key(constraint): constraint for constraint in old_constraints}
    new_by_key = {_constraint_key(constraint): constraint for constraint in new_constraints}

    added = [
        new_by_key[key]
        for key in new_by_key
        if key not in old_by_key
    ]
    removed = [
        old_by_key[key]
        for key in old_by_key
        if key not in new_by_key
    ]
    modified = [
        {
            "from": old_by_key[key],
            "to": new_by_key[key],
        }
        for key in old_by_key.keys() & new_by_key.keys()
        if old_by_key[key] != new_by_key[key]
    ]

    return added, removed, modified


def _constraint_key(constraint: dict[str, Any]) -> tuple[Any, ...]:
    constraint_type = constraint.get("type")
    if constraint_type == "approval_threshold":
        return (
            constraint_type,
            constraint.get("field"),
            constraint.get("operator"),
            constraint.get("requires_role"),
        )
    if constraint_type == "required_role":
        return (constraint_type, constraint.get("value"))
    return (constraint_type,)


def _added_items(
    old_items: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    old_keys = {_item_key(item) for item in old_items}
    return [item for item in new_items if _item_key(item) not in old_keys]


def _removed_items(
    old_items: list[dict[str, Any]],
    new_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    new_keys = {_item_key(item) for item in new_items}
    return [item for item in old_items if _item_key(item) not in new_keys]


def _item_key(item: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    return tuple(sorted(item.items()))


def _deployment_changes(
    old_deployment: dict[str, Any] | None,
    new_deployment: dict[str, Any] | None,
) -> dict[str, list[Any]]:
    if not old_deployment and not new_deployment:
        return {}

    old_deployment = old_deployment or {}
    new_deployment = new_deployment or {}
    changes: dict[str, list[Any]] = {}

    for key in old_deployment.keys() | new_deployment.keys():
        old_value = old_deployment.get(key)
        new_value = new_deployment.get(key)
        if old_value != new_value:
            changes[key] = [old_value, new_value]

    return changes
