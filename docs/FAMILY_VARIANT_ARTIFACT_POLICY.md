# Family Variant Artifact Policy

_Last updated: 2026-03-31_

## Goal

Keep family-variant dashboard artifacts useful for ranking and UI selection without retaining unnecessary heavy data for every tested variant.

This policy now sits under the broader time-series partition rule in `docs/TIME_SERIES_PARTITION_POLICY.md`:
- time-series-heavy artifacts should be partitioned on aligned UTC month boundaries where practical
- dashboard-facing retained heavy files should stay small and selective rather than growing as monoliths

## Retention model

For each family:
- keep lightweight summary/evaluation records for **all tested variants**
- keep full heavy artifacts locally only for the most useful subset:
  - currently **top 1 variant per cluster** within that family
- allow deprecated / disabled variants to remain visible in summary records while removing their heavy artifact files

This means the artifact system should distinguish between:
- **tested variants**
- **retained full variants**
- **deprecated / disabled variants**

## Family-level retention model

Families themselves should also follow a three-tier lifecycle because the family pool will grow over time.

Per cluster:
- **top 1 family** → `active`
- **top 5 families** (excluding active top 1) → `reserve`
- the rest → `archived`

Handling rule is the same as variants:
- `active` families keep heavy dashboard-facing artifacts in local + GitHub working storage
- `reserve` families keep detailed summary/history and are retained for later reranking, but do not need to remain in the local hot set by default
- `archived` families keep summary/history only, while heavy artifacts may be deleted

## Required outputs

### `summary.json`
Must remain the authoritative lightweight summary layer for the family.

It should retain:
- `family`
- `variant_count_total`
- `variant_count_evaluated`
- `variant_count_retained_full`
- `retained_full_variant_ids`
- `composite_summary`
- `cluster_rankings`
- `variant_summaries`

### `variant_summaries`
One record for every tested variant.

Each record should retain:
- `variant_id`
- `family`
- `tested`
- `retained_full`
- `active`
- `deprecated`
- `deprecated_reason`
- overall metrics:
  - `total_return`
  - `max_drawdown`
  - `trade_count`
  - `win_rate`
- per-cluster metrics:
  - `cluster_id`
  - `rank_in_cluster`
  - `avg_utility_1h`
  - `sample_count`
  - `trade_count`
  - `avg_trade_return`
  - `positive_rate`
  - `turnover_count`

### `variants/<variant_id>.json`
Should exist only for retained full variants.

These files may keep the heavy detail needed for deep inspection:
- `summary`
- `curve`
- `ledger`

If a variant is deprecated / disabled and no longer retained as full, its heavy file should be removable without losing the summary record of the test.

## Heavy data that should not be kept for every tested variant

For non-retained variants, do not keep large full-detail payloads indefinitely:
- full equity curve points
- full trade ledger
- signal-level records
- trade-point / switching-point detail
- other large chart-ready arrays not needed for ranking or selection

## Builder implications

The family-variant artifact builder should:
1. evaluate all variants
2. compute cluster-level rankings
3. mark retained full variants (top 1 per cluster for local heavy retention)
4. classify reserve variants (top 10 per cluster, excluding active top 1)
5. write lightweight summary records for all tested variants
6. write full heavy variant files only for retained full variants

## Migration direction

During transition, compatibility monoliths may still exist.
But the target system should move toward:
- lightweight family summary for all tested variants
- heavy variant files only for retained top variants
- no permanent full-detail storage for every losing variant
