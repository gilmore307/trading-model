# Pipeline and Artifact Overview

_Last updated: 2026-03-31_

## Scope example

This overview describes the current intended pipeline for:
- 1 instrument
- 1 strategy family
- ~360 variants

It reflects the latest agreed direction:
- aligned UTC monthly partitions for time-series datasets
- three-tier variant retention (`active` / `reserve` / `archived`)
- detailed family-variant summary records retained even when heavy artifacts are deleted

---

## 1. Raw market data layer

Canonical role:
- factual source layer for all later computation

Examples:
- raw candles
- basis / funding / related market data

### Retention rule
- all time-series datasets should follow aligned UTC month partitions when practical
- default file unit: `YYYY-MM.jsonl`
- target file size: 20–30 MB
- current month can stay open/rewriteable; closed historical months should be sealed

---

## 2. Market-state construction layer

Canonical role:
- turn raw market data into state-feature rows and labels

Examples:
- `crypto_market_state_dataset_v1`
- `unsupervised_market_state_labels_v1`
- label / cluster summaries

### Retention rule
- feature rows and labels should also move toward aligned UTC month partitions
- small derived state summaries should be retained as long-lived lightweight artifacts

---

## 3. Parameter / evaluation research layer

Canonical role:
- offline research and ranking tables used to compare parameter regions, families, and variants

Examples:
- parameter utility datasets
- family / cluster / parameter-region ranking inputs

### Retention rule
- these can remain heavier than dashboard artifacts
- but canonical storage must still be GitHub-friendly at the per-file level
- monolithic whole-history files are transitional/build-time convenience artifacts only, not canonical storage
- large research tables must use a fixed partition standard:
  - first axis: UTC calendar month
  - second axis: family
  - third axis depends on table type:
    - parameter utility datasets -> `parameter-region`
    - cluster/state evaluation tables -> `cluster`
    - variant evaluation/detail tables -> `variant`
- every such dataset must publish a lightweight summary layer in addition to the partitioned detail layer

---

## 4. Variant evaluation layer

For one family with ~360 variants:
- every variant is still evaluated
- but not every variant should keep a permanent heavy artifact

### Output classes
1. lightweight tested summary for every variant
2. retained full artifact only for selected variants

---

## 5. Three-tier variant retention model

### Tier 1 — Active
Definition:
- current top 1 variant per cluster

Storage form:
- local + GitHub
- full heavy artifact retained

Typical use:
- current dashboard usage
- deep inspection
- current composite/routing candidates

### Tier 2 — Reserve
Definition:
- current top 10 variants per cluster, excluding the top 1 active set

Storage form:
- summary kept
- intended as cloud-retained / non-local-hot candidates
- heavy local artifact not required by default

Typical use:
- future reranking when cluster models shift
- backup candidate pool

### Tier 3 — Archived
Definition:
- the rest of the tested variants

Storage form:
- summary only
- heavy artifact removed

Typical use:
- audit trail
- proof that the variant was tested
- historical performance reference

## 6. Three-tier family retention model

Families should follow the same lifecycle logic as variants, but with tighter counts because the family pool is much smaller.

### Tier 1 — Active families
Definition:
- current top 1 family per cluster

Storage form:
- local + GitHub
- full heavy dashboard-facing artifacts retained

Typical use:
- current dashboard family set
- current routing/composite comparison set

### Tier 2 — Reserve families
Definition:
- current top 5 families per cluster, excluding the active top 1 set

Storage form:
- summary retained
- cloud-retained / non-local-hot by default
- local heavy artifacts optional, not default

Typical use:
- fallback candidate pool when cluster behavior changes
- later reranking under newer cluster models

### Tier 3 — Archived families
Definition:
- the rest of the evaluated families

Storage form:
- summary/history only
- heavy artifacts removed

Typical use:
- audit trail
- proof that the family was evaluated and later deprioritized

---

## 7. Family artifact structure

---

## 6. Family artifact structure

Target structure:

```text
family_variant_dashboard/
  <family>/
    summary.json
    composite.json
    variants/
      <variant_id>.json
```

### `summary.json`
Authoritative lightweight management layer for the family.

Should retain:
- family metadata
- `variant_count_total`
- `variant_count_evaluated`
- `variant_count_retained_full`
- retained active/reserve ids when relevant
- cluster rankings
- composite summary
- one summary record for every tested variant

### `composite.json`
Family composite layer.

Should retain:
- composite summary
- composite curve (kept reasonably small)
- cluster-to-selected-variant routing outputs when needed

### `variants/<variant_id>.json`
Heavy detail layer.

Should exist only for variants whose full artifact is intentionally retained.

---

## 7. Required per-variant summary record

Each tested variant should retain a summary record even if its heavy file is deleted.

Required fields include:
- `variant_id`
- `family`
- `tested`
- `tier` (`active` / `reserve` / `archived`)
- `retained_full`
- `active`
- `deprecated`
- `deprecated_reason`
- test/evaluation data range:
  - `instrument`
  - `bar_interval`
  - `data_start`
  - `data_end`
  - `row_count`
  - `partitions_used`
- overall performance:
  - `total_return`
  - `max_drawdown`
  - `trade_count`
  - `win_rate`
  - `signal_count`
  - `turnover_count`
- per-cluster metrics:
  - `cluster_id`
  - `rank_in_cluster`
  - `avg_utility_1h`
  - `sample_count`
  - `trade_count`
  - `avg_trade_return`
  - `positive_rate`

---

## 8. Cluster-version ranking history

Variant summaries should also retain ranking history across cluster-model versions.

Recommended fields:
- `cluster_model_version`
- `ranking_run_id`
- `ranking_timestamp`
- historical `rank_in_cluster`

This allows later comparison such as:
- version 1 → rank 10
- version 2 → rank 5
- version 3 → rank 8

---

## 9. What to delete vs keep

### Keep long term
- raw factual datasets (partitioned)
- market-state summaries
- family summaries
- composite summaries
- tested variant summary records
- ranking history

### Keep selectively
- full heavy artifacts for active variants
- reserve-layer heavy artifacts only when there is a specific reason

### Delete for deprecated / non-retained variants
- full curve
- full ledger
- signal-level detail
- trade-point / switching-point large arrays
- dashboard-unneeded heavy files

---

## 10. Dashboard-facing principle

The dashboard should primarily consume:
- lightweight catalogs
- summary layers
- selective full-detail artifacts

It should not depend on every tested variant permanently retaining full heavy data.

---

## 11. Operational principle

Do not treat one huge family blob as the long-term storage format.

Preferred direction:
- aligned monthly partitions for time-series datasets
- lightweight family summary for all tested variants
- selective full artifacts only for the variants that still matter operationally
- deprecated variants remain visible in summary/history while their heavy artifacts are deleted
