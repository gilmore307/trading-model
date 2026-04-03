# 06 Model Composite and Reporting

This document defines the reporting layer and output boundary.

## Core output types

This repository should publish outputs such as:
- market-only state tables
- state-evaluation tables
- unsupervised state-model artifacts
- cluster/state labels
- state -> preferred-variant mappings
- model composite outputs
- oracle-comparison reports
- comparisons across layer policies

## Primary evaluation output

The main scorecard is the comparison between:
- model composite
- oracle composite

## Required comparison baselines

Do not compare only against:
- default
- state-routed composite
- oracle

Also include at least one simple baseline so the state model must beat something trivial.

Recommended trivial baselines:
- volatility quantile bucket baseline
- return-vol 2D bucket baseline

This helps answer whether the discovered states truly add value beyond simple handcrafted partitioning.

## Oracle-gap report shape

The oracle-gap report should answer:
- where the gap is large
- whether the gap is stable or episodic
- whether routing is reducing the gap

### Section A — overall gap summary
Include:
- `overall_realized_metric`
- `overall_oracle_metric`
- `overall_gap_abs`
- `overall_gap_rel`
- `overall_gap_closure_pct`

Compare at least:
- `global_default`
- `trivial_baseline`
- `state_routed_composite`
- `oracle_composite`

### Section B — by-month gap panel
One row per month:
- `month`
- `realized_metric_default`
- `realized_metric_trivial_baseline`
- `realized_metric_state_routed`
- `oracle_metric`
- `gap_abs_default`
- `gap_abs_trivial_baseline`
- `gap_abs_state_routed`
- `gap_closure_pct_default`
- `gap_closure_pct_trivial_baseline`
- `gap_closure_pct_state_routed`
- `delta_gap_closure_pct`

### Section C — by-state gap table
One row per state:
- `state_id`
- `state_support_n`
- `state_support_pct`
- `oracle_metric_mean`
- `realized_metric_mean`
- `gap_abs`
- `gap_rel`
- `gap_rank`
- `gap_by_month_std`
- `positive_gap_month_ratio`
- `preferred_target`
- `post_routing_realized_metric`
- `post_routing_gap_abs`
- `gap_reduction_abs`
- `gap_reduction_pct`
- `actionability_tag`

Suggested tags:
- `improvement_opportunity`
- `already_well_captured`
- `structurally_hard`
- `uncertain`

### Section D — by-family / by-parameter-region gap panel
One row per family or parameter region:
- `family_id` or `param_region`
- `support_n`
- `oracle_metric_mean`
- `realized_metric_mean`
- `gap_abs`
- `gap_rel`
- `best_states`
- `worst_states`
- `state_concentration_of_gap`

Support `state x family` or `state x param_region` slicing as secondary views when support is sufficient.

## Refresh / versioning contract

Periodic refit makes versioning and identity continuity first-class concerns.

Track at least:
- `state_model_version`
- `state_label_version`
- `mapping_version`
- `refit_window_id`

Also maintain a matching artifact for:
- `old_state_id -> new_state_id`

This contract should support:
- refresh audits
- state continuity analysis
- routing reproducibility

## Output sizing rule

Outputs and reports must not become oversized monolithic files.

Default rule:
- partition outputs early
- prefer many bounded files over one ever-growing file

## Required partition axes

By default, generated outputs should be partitioned by:
- `symbol`
- `family`
- `variant`
- `month`

## Practical partition policy

### State tables
Partition by at least:
- `symbol`
- `month`

### State-evaluation tables
Partition by at least:
- `symbol`
- `family`
- `variant`
- `month`

### Model composite outputs
Partition by at least:
- `symbol`
- `month`

### Oracle-comparison reports
Partition by at least:
- `symbol`
- `family` when family-scoped
- `month`

### State -> preferred-variant mapping outputs
Partition by at least:
- `symbol`
- model/version scope
- optionally `month` or training-window id when mappings are refreshed periodically

## Boundary reminder

Outputs from `trading-model` are model-side research outputs.
They are not live execution actions.
