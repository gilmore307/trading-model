# Model Output Table Quality

## Purpose

This document defines the current quality gate for SQL model-output tables under the six current model contracts, including `_explainability` and `_diagnostics` support tables.

Primary model-output tables should stay focused on row identity, upstream refs, stable scalar score/status fields, and the few resolved values downstream models actually need. Large nested payloads, explanation blocks, reason-code detail, and row-quality evidence belong in `_explainability` or `_diagnostics` tables.

Retired ten-layer output tables may still be audited as migration-source surfaces. They must not define new current contracts.

## Empty Column Policy

Do not fabricate values to make a table look complete. A missing point-in-time source row, option-chain row, event baseline, or reviewed gate should remain visible as missing coverage or a low/zero readiness score.

## Audit Entrypoint

The stable read-only audit entrypoint is:

```bash
PYTHONPATH=src python3 scripts/models/audit_model_output_tables.py --sample-limit 5000
```

The script emits `model_output_table_quality_audit`. It samples a bounded number of rows from the selected model table scope, classifies all-null and sparse columns, and emits review-only cleanup SQL candidates. It never drops columns, rewrites model rows, performs provider calls, activates models, or mutates broker/account state.

By default, the audit uses `model_governance.model_output_audit.MODEL_OUTPUT_TABLES`, which aliases the current six-model table families only. Retained ten-layer tables are exposed separately as `RETAINED_MIGRATION_MODEL_OUTPUT_TABLES` and require `--table-scope retained-migration` or `--table-scope all`.

The stable post-generation gate entrypoint is:

```bash
PYTHONPATH=src python3 scripts/models/run_model_output_quality_gate.py --sample-limit 5000
```

The gate emits `model_output_quality_gate` and exits non-zero when primary model outputs have missing tables, empty tables, unclassified all-null score columns, all-null required refs, support payload generation defects, or stale all-null primary columns. Known long-history/data-accumulation gaps and optional selection gaps are warnings or info, not blockers. Explainability and diagnostic all-null gaps are warnings by default because they may be reviewed support coverage gaps; pass `--strict-support` to make them blocking.

## Generation Rule

`model_governance.model_output_support.write_model_output_with_support` is the canonical writer helper for model-output rows with support payloads. It drops moved nested payload columns from the primary table during generation and writes support rows only when the support payload is non-empty.

Model-specific local fixture scripts may still print compact JSON/JSONL rows with nested payloads for tests and smoke receipts. Those fixture rows are not the persisted SQL artifact contract. Persisted model-output closure is the primary/support split enforced by the SQL writer and quality gates.
