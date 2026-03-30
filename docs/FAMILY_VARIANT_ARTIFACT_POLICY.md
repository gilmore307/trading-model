# Family Variant Artifact Policy

_Last updated: 2026-03-31_

## Goal

Keep family-variant dashboard artifacts useful for ranking and UI selection without retaining unnecessary heavy data for every tested variant.

## Retention model

For each family:
- keep lightweight summary/evaluation records for **all tested variants**
- keep full heavy artifacts only for the most useful subset:
  - currently **top 5 variants per cluster** within that family

This means the artifact system should distinguish between:
- **tested variants**
- **retained full variants**

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
3. mark retained full variants (top 5 per cluster)
4. write lightweight summary records for all tested variants
5. write full heavy variant files only for retained full variants

## Migration direction

During transition, compatibility monoliths may still exist.
But the target system should move toward:
- lightweight family summary for all tested variants
- heavy variant files only for retained top variants
- no permanent full-detail storage for every losing variant
