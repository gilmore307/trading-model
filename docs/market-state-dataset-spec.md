# Market-State Dataset Spec

_Last updated: 2026-03-20_

## Purpose

This document defines the dataset shape for conditional strategy-allocation research.

The training target is not:
- best strategy id

The training target is:
- conditional future utility for a family/parameter configuration under the market state visible at time `t`

## Core row concept

Each training row should represent:

`(market_state_snapshot_t, strategy_family, parameter_vector) -> future_utility_over_H`

This means that for one market timestamp `t`, the research pipeline will usually emit **multiple rows**:
- one row per candidate family/parameter configuration under evaluation

## Dataset layers

## Layer A — market-state snapshot table

One row per timestamp `t`.

Suggested fields:
- `ts`
- `symbol`
- `close`
- `feature_*` columns for engineered market-state features
- `state_prob_*` columns when latent-state model exists
- `state_embedding_*` columns when embedding layer exists
- `state_transition_score`
- `state_uncertainty_score`

This layer describes only the market.
It should not depend on one specific strategy family.

## Layer B — candidate evaluation table

One row per:
- timestamp `t`
- strategy family `s`
- parameter vector `theta`

Suggested core fields:
- `ts`
- `symbol`
- `family`
- `variant_id` or `parameter_region_id`
- explicit parameter columns
- joined market-state feature columns or foreign key to layer A row
- forward utility targets
- risk / cost targets

## Parameter columns

Parameters should be stored explicitly, not hidden only inside a variant id.

Example for MA family:
- `fast_window`
- `slow_window`
- `threshold_enter_pct`
- `threshold_exit_pct`
- `ma_type`
- `price_source`

This is required so later models can learn parameter-performance surfaces.

## Target columns

At minimum include:
- `forward_return_H`
- `forward_max_drawdown_H`
- `forward_turnover_H`
- `forward_trade_count_H`
- `switch_cost_estimate`
- `slippage_cost_estimate`
- `net_utility_H`

Recommended utility form:

`net_utility_H = return - alpha*drawdown - beta*turnover - gamma*switch_cost - delta*slippage`

The exact coefficients may vary by experiment, but the raw components should be preserved separately.

## Horizon design

Multiple horizons should usually be stored.

Suggested first-wave horizons:
- short horizon
- medium horizon
- family-specific operational horizon if needed

Example names:
- `forward_return_15m`
- `forward_return_1h`
- `forward_return_4h`
- `net_utility_15m`
- `net_utility_1h`
- `net_utility_4h`

This allows later selector logic to compare sensitivity to horizon choice.

## Candidate generation rule

For each timestamp `t` used in research:
1. compute market-state snapshot using only data available up to `t`
2. enumerate the candidate family/parameter configurations being studied
3. evaluate forward utility for each candidate over allowed future window `H`
4. store one row per candidate

This creates the full conditional-performance dataset required by family scorers and parameter-surface models.

## Leakage rules

Strict rules:
- no future-derived features in market-state snapshot
- latent states must be fit only on past data in walk-forward experiments
- future utility targets must be separated cleanly from present features
- no full-sample normalization that leaks future distribution shape unless explicitly re-estimated in each walk-forward segment

## Storage recommendation

Preferred outputs:
- normalized parquet for large-scale modeling
- json/jsonl summaries for audit and dashboard use
- explicit schema version field in every exported artifact

Suggested metadata fields:
- `dataset_version`
- `feature_inventory_version`
- `candidate_registry_version`
- `utility_definition_version`
- `generated_at`

## Research artifacts derived from this dataset

This dataset should support at least four output types:

1. **State x Family summary**
2. **State x Family x Parameter Region cube**
3. **Family scorer training set**
4. **Parameter surface model training set**

## Dashboard implication

The dashboard should eventually expose this dataset through summary layers rather than raw row dumps.

First useful dashboard views:
- state summary view
- family ranking per state
- parameter-region ranking inside selected family
- confidence / transition-state overlays

## Immediate implementation target

The first implementation does not need the final full latent-state stack.

It only needs:
- a stable feature snapshot per timestamp
- candidate family/parameter rows
- forward utility outputs
- consistent schema/versioning

That is enough to start building the performance cube and training later conditional models.
