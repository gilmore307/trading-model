# 04 Repo Structure and Implementation Status

This document summarizes the intended repo structure and the current implementation state.

## Intended structure
- `docs/`
- `src/trading_model/contracts/`
- `src/trading_model/io/`
- `src/trading_model/features/`
- `src/trading_model/discovery/`
- `src/trading_model/evaluation/`
- `src/trading_model/reporting/`
- `src/trading_model/pipeline/`
- `src/trading_model/utils/`
- `src/trading_model/config/`

Code organization should remain centered on:
- input alignment
- unsupervised modeling
- state evaluation
- offline report generation

Do not reintroduce runtime/orchestration ownership here.

## Current implementation progress

A new minimal implementation skeleton now exists under `src/trading_model/`.

What is already wired:
- market bar loading from `trading-data`
- base-only v1 feature construction for stage 1
- winsorization + robust scaling before clustering
- candidate-`k` model selection for GMM/KMeans
- state-table generation with confidence fields
- first-pass stability report generation
- variant loading from `trading-strategy` outputs
- global-oracle loading from `trading-strategy` outputs
- state-evaluation table construction with attach-status / attach-delta audit fields
- first winner-mapping artifact generation
- first execution-facing confidence / opportunity-strength artifact fields on winner mappings
- first oracle-gap report generation
- first trivial-baseline policy wiring
- partitioned CSV output writing for state tables, state-evaluation tables, winner mappings, and trivial-baseline policy outputs
- first research-verdict output
- first multi-symbol availability scan and summary entrypoint
- multi-symbol summary now carries execution-confidence summary fields so cross-symbol ranking can inspect both coverage and model-decision strength

## Current artifact shape

The repo now writes:
- top-level per-symbol summary/judgment artifacts for convenience/debugging where the object is naturally compact
- bounded partitioned artifacts as the canonical downstream layout for large table-like outputs

Canonical partition pattern now includes:
- state tables: `symbol / month`
- model selection: `symbol / state_model_version`
- stability report: `symbol / state_model_version`
- state-evaluation tables: `symbol / family / variant / month`
- winner mappings: `symbol / mapping_version`
- trivial-baseline policy: `symbol / trivial_baseline_id`
- oracle-gap by-month report records: `symbol / month`
- oracle-gap by-state report records: `symbol / winner_type / preferred_target`
- oracle-gap summary object: `symbol`
- research verdict: `symbol / month_scope`
- multi-symbol summary per-symbol row slices: `symbol`
- multi-symbol summary full object: `scope=all`

Canonical downstream expectation:
- partitioned artifacts under `outputs/<symbol>/partitions/` (or the configured output root's equivalent partition tree) should be treated as the stable machine-facing contract when the artifact is naturally partition-shaped
- choose partition keys from the artifact's own semantics and lifecycle, not from a fixed template
- high-row, appendable, lifecycle-sensitive tables should be partitioned aggressively
- small single-object summaries or cross-symbol conclusions may remain canonical as a whole object even if auxiliary per-symbol slices also exist
- large top-level aggregate table exports should not be generated; large table-like outputs should be emitted directly in partitioned form
- top-level compact csv/json artifacts may still be retained as convenience/debug outputs when the object is naturally small
- partition writers now enforce a single-file target cap of `<= 50 MB`
- chunk splitting is only a safety backstop after semantic partitioning, not the primary partition strategy
- if a would-be partition file exceeds that cap, the writer must emit additional chunk files such as `.part-0001`, `.part-0002`, and so on under the same partition directory

Artifact-specific conclusion at the current stage:
- `state_table` and `state_evaluation_table` are the strongest cases for fine-grained semantic partitioning because they are the largest, most append-like, and most lifecycle-sensitive artifacts; they should be generated directly as partitioned outputs rather than as giant top-level exports
- `model_selection`, `stability_report`, and `winner_mapping` are naturally version-scoped judgment artifacts and do not need forced row-level splitting beyond their current symbol/version boundary unless evidence later shows otherwise
- `multi_symbol_summary` is the primary global summary object; per-symbol slices are helpful for convenience/indexing, but the full-object view remains the natural canonical interpretation
- a separate top-level `aggregate_cross_symbol_verdict.json` is unnecessary when the same content already lives inside `multi_symbol_summary.json`

This means the partition layout is now materially defined across both main tables and summary/report surfaces, while lifecycle/retention decisions over older partitions remain manager-owned.

## Boundary audit result

Current code reads market bars only from `trading-data` and strategy/oracle artifacts only from `trading-strategy`.
No active raw-market reacquisition or in-repo `data/raw/*` write path is present in the current minimal pipeline.

## What is still intentionally rough
- attach-status logic should be tightened to exact-vs-previous-bar audit fidelity
- strategy-side forward-horizon fields still need richer upstream alignment
- oracle-gap reporting is still a compact v1 report, not the full four-layer contract
- model-selection/stability logic is still heuristic and not yet fully threshold-calibrated

## Repo-normalization review result

The active code tree is now aligned to the intended offline boundary.
There are no remaining stale hybrid runtime trees that still need separate migration handling.
