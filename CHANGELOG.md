# Changelog

## 0.2.0 - 2026-05-17

Governance-Ledger v0.2.0 is a major release that repositions Ledger as governance compiler and semantic validation infrastructure.

### Added

- Governance normalization engine with statement classification, normalized statement traces, and coverage reporting.
- Semantic diagnostics for ambiguous authority, weak coverage, overlapping thresholds, duplicate requirements, and compiler validation issues.
- Governance compilation reports with source identity, normalized statements, diagnostics, compiler summaries, and deterministic report hashes.
- Publication gating based on validation errors and blocking compiler diagnostics.
- Authority provenance chain using `governance_authority_lineage.v1`.
- Lineage verification CLI through `verify-lineage`.
- Governance replay tooling through `replay-authority` and `replay-execution`.
- Publication integrity checks for contract, manifest, registry, deployed review, and snapshot transactions.
- Canonical JSON schemas for governance source identity, diagnostics, compilation reports, replay requests, publication manifests, registries, reviews, and snapshots.
- Registry integrity hashing and normalized publication paths.
- Normalization corpus tests for domain policy examples.

### Changed

- Reframed Ledger from earlier extraction-centered workflows to deterministic governance operationalization infrastructure.
- Publishing now treats lineage as Ledger-owned publication evidence and stamps it onto compiled authority contracts before manifest and registry assembly.
- Runtime integration now relies on installed package contracts rather than local checkout path resolution.
- Package version bumped to `0.2.0`.

### Removed

- Local integration path resolution helper.
- Guard compatibility shim for missing replay admissibility exports.
- Test-time imports that pointed at monorepo integration paths.

### Verification

- Full test suite passes with `96` tests.

## 0.1.1 - 2026-05-10

- Early deterministic governance ledger workflows.
- Review lifecycle transitions.
- Basic policy normalization and validation.
- Publication artifacts, manifests, registry entries, snapshots, and rollback support.
