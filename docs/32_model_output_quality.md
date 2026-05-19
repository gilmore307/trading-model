# Model Output Table Quality

## Purpose

This document defines the current quality gate for SQL model-output tables under `trading_model.model_01_*` through `trading_model.model_09_*`, including `_explainability` and `_diagnostics` support tables.

Primary model-output tables should stay focused on row identity, upstream refs, stable scalar score/status fields, and the few resolved values downstream layers actually need. Large nested payloads, explanation blocks, reason-code detail, and row-quality evidence belong in `_explainability` or `_diagnostics` tables.

## Empty Column Policy

Empty columns are not all the same issue:

- missing optional evidence, such as no option contract or no reviewed event gate, is valid when the model explicitly records it as missing evidence;
- sparse score columns usually mean upstream data coverage is incomplete and should be tracked as a data-quality gap;
- known all-null long-history or selection columns are data accumulation gaps when the input window lacks enough point-in-time evidence;
- empty support payload columns indicate a generator/support-table bug and should be repaired;
- stale all-null primary columns should stop being emitted and may be dropped only through reviewed SQL cleanup.

Do not fabricate values to make a table look complete. A missing point-in-time source row, option-chain row, event baseline, or reviewed gate should remain visible as missing coverage or a low/zero readiness score.

## Audit Entrypoint

The stable read-only audit entrypoint is:

```bash
PYTHONPATH=src python3 scripts/models/audit_model_output_tables.py --sample-limit 5000
```

The script emits `model_output_table_quality_audit`. It samples a bounded number of rows from all nine primary model tables and support tables, classifies all-null and sparse columns, and emits review-only cleanup SQL candidates. It never drops columns, rewrites model rows, performs provider calls, activates models, or mutates broker/account state.

The stable post-generation gate entrypoint is:

```bash
PYTHONPATH=src python3 scripts/models/run_model_output_quality_gate.py --sample-limit 5000
```

The gate emits `model_output_quality_gate` and exits non-zero when primary model outputs have missing tables, empty tables, unclassified all-null score columns, all-null required refs, support payload generation defects, or stale all-null primary columns. Known long-history/data-accumulation gaps and optional selection gaps are warnings or info, not blockers. Explainability and diagnostic all-null gaps are warnings by default because they may be reviewed support coverage gaps; pass `--strict-support` to make them blocking.

## Generation Rule

`model_governance.model_output_support.write_model_output_with_support` is the canonical writer helper for model-output rows with support payloads. It drops moved nested payload columns from the primary table during generation and writes support rows only when the support payload is non-empty.
