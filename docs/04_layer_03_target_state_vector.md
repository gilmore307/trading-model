# Layer 03 - TargetStateVectorModel

Status: Accepted direction; implementation contract pending.

Layer 3 is reset from strategy-family/variant selection to target state-vector construction. The previous strategy-family/variant work is frozen as a legacy experiment and must not be expanded until the new target-state boundary is accepted.

## Purpose

`TargetStateVectorModel` answers:

> Given the broad market state, sector/industry state, and a single anonymous target's own tape/liquidity behavior, what is the target's current tradable market state?

Layer 3 should find the relationship between **target board/tape state** and future trading outcomes. It should not begin by choosing a strategy variant. A detailed variant grid is not useful unless its variables are connected to market/sector/target state conditions.

Layer 3 builds a point-in-time state vector that later layers may use to decide trade quality, strategy expression, option expression, and portfolio risk.

## Boundary reset

Layer 3 owns:

- anonymous target candidate state construction;
- market-context, sector-context, and target-local feature fusion;
- target state vector generation;
- target-state labels for future return/risk/tradability relationship research;
- state-cluster / embedding / regime evidence for a single target candidate;
- acceptance evidence that state vectors explain future tradeable outcomes better than market-only or sector-only baselines.

Layer 3 does **not** own:

- strategy family selection;
- parameter variant expansion/pruning;
- exact entry/exit orders;
- option DTE, strike, delta, premium, IV/Greeks, or contract ID;
- position size, portfolio weight, hedge ratio, or execution policy;
- live/paper broker interaction.

## Input flow

```text
trading_model.model_01_market_regime       # broad market_context_state
trading_model.model_02_sector_context      # sector_context_state / selected basket context
anonymous_target_candidate_builder         # point-in-time anonymous candidate rows
trading_data.source_03_target_state        # target-local bars, liquidity, quote/trade evidence
trading_data.feature_03_target_state_vector
                                           # deterministic target-state feature surface
-> TargetStateVectorModel
-> trading_model.model_03_target_state_vector
```

The existing `source_03_strategy_selection` and `feature_03_strategy_selection` names are legacy implementation artifacts. They may be reused temporarily during migration only if the request explicitly marks them as compatibility paths. New contracts should use target-state names.

## Core state-vector components

Layer 3 vectors must be explicitly decomposable into three blocks.

| Block | Required role | Example evidence classes |
|---|---|---|
| Market state block | Describe the current broad environment inherited from Layer 1. | market regime, volatility/risk state, trend breadth, liquidity stress, correlation/risk-on-risk-off background. |
| Sector state block | Describe the target's sector/industry context inherited from Layer 2. | sector trend stability, sector rotation rank, sector volatility, basket liquidity, selected/prioritized sector handoff, sector-vs-market relative strength. |
| Target state block | Describe the anonymous target's own board/tape condition. | target trend, returns, volatility, ATR%, gap, range location, volume/dollar-volume, spread/liquidity, VWAP distance, high/low breakout/reversion state, compression/expansion, abnormal activity. |

Layer 3 may also derive cross-block relational features when they are point-in-time and identity-safe:

- target relative strength versus sector and market;
- target volatility versus sector and market;
- target liquidity/cost versus sector peers or accepted universe reference;
- target beta/correlation to market and sector;
- sector-confirmed versus sector-divergent target movement;
- idiosyncratic move score after market/sector adjustment.

## Canonical output shape

Proposed model output table when promoted:

```text
trading_model.model_03_target_state_vector
```

Minimum row identity:

```text
available_time
tradeable_time
target_candidate_id
market_context_state_ref
sector_context_state_ref
3_target_state_vector_id
3_target_state_vector_ref
```

Model-facing payload groups:

```text
market_state_features
sector_state_features
target_state_features
cross_state_features
target_state_embedding
state_cluster_id
state_quality_diagnostics
```

Audit/routing metadata must remain outside model-facing fitting vectors:

```text
audit_symbol_ref
routing_symbol_ref
source_sector_or_industry_symbol
source_holding_ref
source_stock_etf_exposure_ref
```

`target_candidate_id` is a row key only. It must not become a categorical fitting feature.

## Labels and learning objective

Layer 3 labels should describe future target-state outcomes, not strategy variant wins.

Initial label families:

| Label family | Purpose |
|---|---|
| Forward return distribution | What the target did after this state over reviewed horizons. |
| Forward volatility / path risk | Whether the state led to smooth movement, chop, gap risk, or adverse excursion. |
| Directional persistence | Whether movement persisted after market/sector adjustment. |
| Reversion pressure | Whether stretched states reverted toward local/sector/market anchors. |
| Liquidity/tradability | Whether the target remained tradeable after costs/spreads/volume constraints. |
| State transition | Which target state usually follows this state. |

These labels should be evaluated across multiple horizons, but horizon choices are label axes, not strategy variants.

## Relationship-first research questions

Layer 3 review should ask:

1. Which target states produce stable forward edge after controlling for market and sector state?
2. Which target moves are sector-confirmed versus idiosyncratic?
3. Which target states are tradeable after liquidity/cost gates?
4. Which states are directionally persistent, mean-reverting, or noise/chop?
5. Which market/sector states make a target-local pattern useful or useless?
6. Does adding target state improve prediction versus market-only and market+sector baselines?

## Migration from legacy strategy-variant work

Legacy assets under `src/models/model_03_strategy_selection/` and `trading-data` `feature_03_strategy_selection` are frozen. They may be useful later as downstream probes or diagnostic labels, but they are no longer the Layer 3 source of truth.

Migration order:

1. Freeze strategy-family/variant expansion.
2. Promote this Layer 3 target-state contract.
3. Add `model_03_target_state_vector` package and tests.
4. Add `trading-data` source/feature target-state request boundary.
5. Build baseline target-state vectors from bars/liquidity plus Layer 1/2 refs.
6. Add forward state/outcome labels and market-only / sector-only baselines.
7. Only after state/outcome relationships are accepted, revisit strategy/variant selection as a later layer or downstream decision surface.

## Acceptance gates

A Layer 3 implementation is not accepted unless it proves:

- point-in-time construction with `available_time` and `tradeable_time` separation;
- raw ticker/company identity excluded from model-facing vectors;
- market, sector, target, and cross-state blocks are separately inspectable;
- target-state labels are future-aware only in training/evaluation, never in inference features;
- baselines compare market-only, market+sector, and market+sector+target vectors;
- state vectors improve at least one accepted forward outcome relationship with split-stability evidence;
- liquidity/cost diagnostics identify states that are theoretically predictive but practically untradeable;
- audit/routing metadata can map decisions back to real symbols without leaking identity into fitting vectors;
- generated outputs, large artifacts, and credentials stay out of Git.
