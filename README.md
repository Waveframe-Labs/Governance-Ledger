---
title: "Governance-Ledger"
document_type: "overview"
system: "Governance-Ledger"
component: "core"
version: "0.2.0"
status: "draft"

created: "2026-05-08"
updated: "2026-05-17"

authors:
  - "Waveframe Labs"

maintainers:
  - "Waveframe Labs"

license: "Apache-2.0"

repository: "https://github.com/Waveframe-Labs/Governance-Ledger"

summary: >
  Governance-Ledger is governance compiler and semantic validation
  infrastructure for deterministic governance operationalization.
---

# Governance-Ledger

Governance-Ledger turns governed source text into deterministic, reviewable, publishable governance authority. It is best understood as **Governance Compiler + Semantic Validation Infrastructure**.

Ledger is not an AI policy interpreter, workflow automation layer, orchestration engine, or runtime execution system. It does not guess meaning from policy language. It normalizes supported governance statements, emits semantic diagnostics for unsafe or ambiguous structure, gates publication, preserves lineage, and makes governance authority replayable.

## What It Provides

- Governance normalization from source text into canonical governance statements.
- Semantic diagnostics for ambiguous, conflicting, incomplete, or unsafe authority.
- Governance compilation reports with coverage, diagnostics, statement traces, and report hashes.
- Publication gating so governance authority cannot be published when blocking diagnostics are present.
- Provenance chains from source governance to compilation reports to published authority contracts.
- Publication manifests and contract registries with integrity hashes.
- Lineage verification for authority artifacts.
- Replay tooling for compilation and admissibility evidence.
- Deterministic snapshots, rollback artifacts, diffs, and review lifecycle state.
- Canonical schemas for generated governance, diagnostics, replay, publication, review, registry, and snapshot artifacts.

## Why This Exists

Governance used by runtime systems must be deterministic, inspectable, and reproducible. Human governance language can enter the system, but publication authority should only come from normalized statements, explicit diagnostics, approved reviews, canonical compilation reports, and traceable provenance.

Governance-Ledger exists to make that path auditable:

```text
Governance Source
  -> Normalized Statements
  -> Semantic Diagnostics
  -> Governance Compilation Report
  -> Human Review and Approval
  -> Published Authority Contract
  -> Manifest, Registry, Snapshot
  -> Lineage Verification and Replay
```

## Core Concepts

**Governance normalization**

Ledger classifies governance statements and converts supported language into canonical policy structures. Unsupported or ambiguous language remains visible as diagnostics; it is not silently converted into executable authority.

**Semantic diagnostics**

Diagnostics identify governance risks such as missing authority, overlapping thresholds, duplicate roles, weak normalization coverage, and publication-blocking compiler issues. Diagnostics are structured artifacts with stable codes, severity, domains, and publication impact.

**Governance compilation reports**

Compilation reports bind source governance identity, normalized statement traces, coverage metrics, diagnostics, compiler summaries, and a deterministic `report_hash`. They are evidence objects, not log output.

**Publication gating**

Publishing requires an approved review and generated policy that passes compiler-ingestion validation. Blocking diagnostics prevent publication. Published contract, manifest, registry, deployed review, and snapshot artifacts are written as one transaction.

**Lineage verification**

Published authority contracts include `governance_authority_lineage.v1` linking the authority to source governance and compilation report hashes. Ledger can verify that lineage independently.

**Replayability**

Replay tooling reproduces compilation evidence from source governance and can replay admissibility decisions against authority and execution state. Replay failures produce diagnostics rather than silent disagreement.

**Deterministic governance operationalization**

Ledger records governance state transitions and publication artifacts with deterministic identifiers, hashes, normalized paths, immutable publication outputs, and rollback-capable snapshots.

## What It Is Not

Governance-Ledger is not:

- AI policy interpretation.
- Legal advice or legal reasoning.
- A workflow automation product.
- An orchestration engine.
- A runtime mutation executor.
- A replacement for CRI-CORE Contract Compiler semantics.
- A replacement for Waveframe Guard runtime enforcement.
- A system that infers unsupported governance meaning.

## Install

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install governance-ledger
```

Ledger relies on installed package contracts for integration behavior:

- `cricore-contract-compiler>=0.3.0`
- `waveframe-guard>=0.5.0`

Local checkout path resolution is not part of production behavior.

## Command Workflow

Generate normalized governance drafts and validation artifacts:

```powershell
governance-ledger run policies/
```

Check publication readiness:

```powershell
governance-ledger check generated/
```

Approve a reviewed governance artifact:

```powershell
governance-ledger approve reviews/finance_policy.review.json --actor governance-team
```

Publish approved governance authority:

```powershell
governance-ledger publish reviews/finance_policy.review.json
```

Inspect published authority:

```powershell
governance-ledger list contracts
governance-ledger show contracts/finance-policy-0.1.0.contract.json
```

Verify authority lineage:

```powershell
governance-ledger verify-lineage --contract contracts/finance-policy-0.1.0.contract.json
```

Replay source governance into compilation evidence:

```powershell
governance-ledger replay-authority `
  --source policies/finance_policy.txt `
  --report reviews/finance_policy.deployed.review.json `
  --contract contracts/finance-policy-0.1.0.contract.json
```

Replay execution admissibility:

```powershell
governance-ledger replay-execution `
  --contract contracts/finance-policy-0.1.0.contract.json `
  --execution-state execution_state.json
```

## Artifact Layout

```text
policies/      source governance text
generated/     normalized policy drafts and validation artifacts
reviews/       review, approval, compilation, and deployment evidence
contracts/     immutable published authority contracts, manifests, registry
snapshots/     deterministic governance state snapshots
schemas/       canonical JSON schemas
```

Publication produces:

- `contracts/<contract-id>-<version>.contract.json`
- `contracts/<policy>.publication_manifest.json`
- `contracts/index.json`
- `reviews/<policy>.deployed.review.json`
- `snapshots/<snapshot-id>.json`

Publication artifacts use normalized POSIX-style paths such as `contracts/finance-policy-0.1.0.contract.json`, even on Windows.

## Example Normalization

Source governance:

```text
Transfers above $1M require manager approval.
Requester and approver must be separate.
All transfer approvals must be recorded for audit purposes.
```

Normalized policy excerpt:

```json
{
  "contract_id": "finance-policy",
  "contract_version": "0.1.0",
  "authority": {
    "required_roles": ["manager"],
    "separation_of_duties": true
  },
  "approvals": {
    "required": [
      {
        "role": "manager",
        "condition": {
          "field": "amount",
          "operator": ">",
          "value": 1000000
        }
      }
    ],
    "thresholds": [
      {
        "field": "amount",
        "operator": ">",
        "value": 1000000,
        "requires_role": "manager"
      }
    ]
  },
  "artifacts": {
    "required": ["approval_audit_record"]
  }
}
```

## Diagnostics and Gates

Validation artifacts and review artifacts include structured warnings and compiler diagnostics. A diagnostic may be informational, warning-level, or publication-blocking.

Examples of publication-blocking conditions:

- Ambiguous authority, such as approval without a named approving role.
- Low governance normalization coverage.
- Overlapping approval thresholds.
- Duplicate or conflicting approval requirements.
- Compiler schema violations.
- Missing or mismatched provenance lineage.

`governance-ledger check generated/` exits non-zero when validation contains error-severity diagnostics.

## Lineage and Integrity

Published authority contracts include lineage:

```json
{
  "lineage": {
    "schema_version": "governance_authority_lineage.v1",
    "source_hash": "sha256:...",
    "compilation_report_hash": "sha256:...",
    "review_id": "review-finance_policy"
  }
}
```

Publication manifests and registries carry source and report hashes so consumers can verify the authority chain without trusting local build state.

## Schemas

Canonical schemas live in [schemas/](schemas/), including:

- Governance source identity.
- Governance diagnostics.
- Governance compilation reports.
- Replay authority requests.
- Replay execution requests.
- Publication manifests.
- Contract registries.
- Reviews.
- Snapshots.

## Documentation

- [CHANGELOG.md](CHANGELOG.md)
- [GOVERNANCE_OBJECT_MODEL.md](GOVERNANCE_OBJECT_MODEL.md)
- [LIFECYCLE.md](LIFECYCLE.md)
- [PROVENANCE.md](PROVENANCE.md)
- [NON_GOALS.md](NON_GOALS.md)
- [schemas/](schemas/)
