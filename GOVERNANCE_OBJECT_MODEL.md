# Governance Object Model

This document describes the deterministic governance objects produced and transformed by Governance Authoring.

The object model is the project ontology: governance text becomes structured state, and state evolves through explicit artifacts.

## Review Object

A review object is the central governance authoring artifact.

```json
{
  "review_id": "review-001",
  "created_at": "2026-05-07T20:14:00Z",
  "source_document": "finance_policy.txt",
  "review_status": "pending",
  "detected_constraints": [],
  "warnings": []
}
```

Fields:

- `review_id`: stable review identifier.
- `created_at`: review artifact creation timestamp.
- `source_document`: source policy document name when known.
- `review_status`: lifecycle state.
- `detected_constraints`: deterministic extracted governance primitives.
- `warnings`: unsupported, ambiguous, or unextracted governance language.

## Detected Constraints

Role requirement:

```json
{
  "type": "required_role",
  "value": "manager",
  "source_text": "require manager approval"
}
```

Separation of duties:

```json
{
  "type": "separation_of_duties",
  "value": true,
  "source_text": "must be separate"
}
```

Approval threshold:

```json
{
  "type": "approval_threshold",
  "operation": "transfer_funds",
  "value": 1000000,
  "source_text": "above $1M"
}
```

## Warnings

Warnings make governance loss visible.

Unsupported constraint:

```json
{
  "type": "unsupported_constraint",
  "text": "reasonable approval timing"
}
```

Ambiguous authority:

```json
{
  "type": "ambiguous_authority",
  "text": "appropriate manager"
}
```

Extraction gap:

```json
{
  "type": "extraction_gap",
  "text": "Transfers shall be reviewed quarterly."
}
```

## Lifecycle Entries

Lifecycle entries record state evolution.

```json
{
  "from_status": "pending",
  "to_status": "reviewed",
  "actor": "governance-team",
  "timestamp": "2026-05-07T20:14:00Z",
  "note": "Reviewed extracted constraints."
}
```

Rollback entries are also lifecycle entries, but they record restoration provenance:

```json
{
  "from_snapshot": "snapshot-abc123",
  "rollback_actor": "ops-team",
  "rollback_reason": "restore approved governance",
  "rolled_back_at": "2026-05-07T22:00:00Z"
}
```

## Compiled Contract Linkage

Governance Authoring does not embed compiled contracts. It records lightweight linkage only.

```json
{
  "compiled_contract": {
    "contract_id": "finance-core",
    "contract_version": "1.0.0",
    "contract_hash": "abc123"
  },
  "compiled_by": "compiler-service",
  "compiled_at": "2026-05-07T20:30:00Z"
}
```

The full compiled contract remains an external artifact owned by the canonical compiler.

## Deployment Provenance

Deployment provenance records where a compiled governance contract was activated.

```json
{
  "deployment": {
    "environment": "production",
    "runtime": "waveframe-guard",
    "enforcement_engine": "cricore",
    "engine_version": "0.12.0",
    "deployed_by": "ops-team",
    "deployed_at": "2026-05-07T21:00:00Z"
  }
}
```

## Snapshot Object

A snapshot freezes a review state.

```json
{
  "snapshot_id": "snapshot-abc123",
  "created_at": "2026-05-07T21:30:00Z",
  "review_id": "review-001",
  "review_status": "deployed",
  "snapshot_hash": "abc123...",
  "review": {}
}
```

The `snapshot_hash` is deterministic over canonical JSON for the embedded review state.

## Rollback Provenance

Rollback restores a review from a validated snapshot and appends rollback provenance.

```json
{
  "rollback": {
    "from_review_id": "review-001",
    "from_review_status": "deployed",
    "to_snapshot_id": "snapshot-abc123",
    "to_review_id": "review-001",
    "to_review_status": "approved",
    "rollback_actor": "ops-team",
    "rollback_reason": "restore approved governance",
    "rolled_back_at": "2026-05-07T22:00:00Z"
  }
}
```

Rollback is a governance event. It does not erase history.

## Diff Structure

Review diffs compare governance versions.

```json
{
  "added_constraints": [],
  "removed_constraints": [],
  "modified_constraints": [],
  "new_warnings": [],
  "resolved_warnings": [],
  "deployment_changes": {
    "engine_version": ["0.12.0", "0.13.0"]
  }
}
```

Diffs are structural, not semantic guesses.
