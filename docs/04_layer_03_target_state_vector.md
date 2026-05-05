# Layer 03 - TargetStateVectorModel

Status: Accepted direction-neutral tradability boundary; implementation contract pending.

Layer 3 is target state-vector construction. Earlier action/variant Layer 3 work is retired and must not be used as the active Layer 3 boundary.

## Purpose

`TargetStateVectorModel` answers:

> Given the broad market state, sector/industry state, and a single anonymous target's own tape/liquidity behavior, what is the target's current tradable market state?

Layer 3 should find the relationship between **target board/tape state** and future trading outcomes. It should not begin by choosing a downstream action variant.

Layer 3 builds a point-in-time, direction-neutral tradability state vector that later layers may use to estimate direction confidence, trading projection, expression fit, and portfolio risk. Layer 3 does not output position size or final action.

## Boundary reset

Layer 3 owns:

- anonymous target candidate construction as preprocessing / sample organization, not as a separate model;
- market-context, sector-context, and target-local feature fusion;
- target state vector generation;
- target-state labels for future return/risk/path/tradability relationship research, kept out of inference features;
- state-cluster / embedding / regime evidence for a single target candidate;
- acceptance evidence that state vectors explain future tradeable outcomes better than market-only or sector-only baselines.

Layer 3 does **not** own:

- strategy selection;
- parameter expansion/pruning;
- exact entry/exit orders;
- option DTE, strike, delta, premium, IV/Greeks, or contract ID;
- direction-confidence calibration, position size, portfolio weight, hedge ratio, or execution policy;
- live/paper broker interaction.

## Input flow

```text
trading_model.model_01_market_regime       # broad market_context_state
trading_model.model_02_sector_context      # sector_context_state / selected basket context
Layer 3 preprocessing: anonymous_target_candidate_builder
                                           # point-in-time anonymous candidate rows and anonymous_target_feature_vector
trading_data.source_03_target_state        # target-local bars, liquidity, quote/trade evidence
trading_data.feature_03_target_state_vector
                                           # deterministic target-state feature surface
-> TargetStateVectorModel
-> trading_model.model_03_target_state_vector
```

## Core state-vector components

Detailed V1 contract:

```text
src/models/model_03_target_state_vector/target_state_vector_contract.md
```

Use `docs/92_vector_taxonomy.md` for vocabulary. `anonymous_target_feature_vector` is the Layer 3 preprocessing/input vector; `target_state_vector` is the Layer 3 model output.

Layer 3 output state vectors must be explicitly decomposable into four model-facing blocks.

| Block | Required role | Example evidence classes |
|---|---|---|
| `market_state_features` | Describe the current broad environment inherited from Layer 1. | market direction state, trend quality, volatility/risk state, transition risk, trend breadth, liquidity stress, correlation/risk-on-risk-off background. |
| `sector_state_features` | Describe the target's sector/industry context inherited from Layer 2. | sector relative direction, trend quality/stability, transition risk, basket liquidity/tradability, handoff state, handoff bias, sector-vs-market relative state. |
| `target_state_features` | Describe the anonymous target's own board/tape condition. | target state direction, trend quality, path stability/noise, transition risk, volatility, ATR%, gap, range location, volume/dollar-volume, spread/liquidity, VWAP distance, session position, abnormal activity. |
| `cross_state_features` | Describe the target's relationship to market and sector state. | beta-adjusted target-vs-sector/market residual direction, relative trend quality, volatility ratios, beta/correlation, sector-confirmed/divergent movement, idiosyncratic residual state, context support. |

Layer 3 may also derive cross-block relational features when they are point-in-time and identity-safe:

- target residual direction / relative behavior versus sector and market;
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

## Direction-neutral score semantics

Layer 3 score families must stay separated:

- `3_target_direction_score_<window>` is signed current-state direction evidence. It is not Layer 4 alpha confidence and is not a position instruction.
- `3_target_trend_quality_score_<window>` and `3_target_path_stability_score_<window>` describe whether the state has a clean tradable structure.
- `3_target_transition_risk_score_<window>` and `3_target_noise_score_<window>` describe failure/whipsaw risk and should usually reduce handoff quality.
- `3_target_liquidity_tradability_score` describes execution friendliness and cost pressure.
- `3_tradability_score_<window>` is direction-neutral; stable downtrends can score highly when quality, stability, liquidity, and context support are strong.
- `3_state_quality_score`, coverage, and data-quality diagnostics describe reliability of the state row, not opportunity.

Context alignment should not collapse signed direction and quality. Prefer separate current-state fields such as `3_context_direction_alignment_score_<window>` for signed alignment and `3_context_support_quality_score_<window>` for direction-neutral support quality.

## Labels and learning objective

Layer 3 labels should describe future target-state outcomes, not downstream strategy/action wins.

Initial label families:

| Label family | Purpose |
|---|---|
| Signed forward return distribution | Direction-neutral outcome using a deterministic point-in-time state orientation; not model-fitted alpha confidence. |
| Forward volatility / path risk | Whether the state led to smooth movement, chop, gap risk, or adverse excursion. |
| Directional persistence | Whether current-state direction persisted after market/sector adjustment. |
| Reversion pressure | Whether stretched states reverted toward local/sector/market anchors. |
| Liquidity/tradability | Whether the target remained tradeable after costs/spreads/volume constraints. |
| State transition | Which target state usually follows this state. |

These labels should be evaluated across multiple horizons, but horizon choices are label axes, not a variant universe. If signed labels use an orientation sign, the sign must come from deterministic point-in-time state evidence or an out-of-sample upstream prediction, never from the same fitted target being evaluated.

## Relationship-first research questions

Layer 3 review should ask:

1. Which target states are clean, stable, low-noise, low-transition-risk, and tradable after controlling for market and sector state?
2. Which target moves are sector-confirmed versus idiosyncratic?
3. Which target states are tradeable after liquidity/cost gates?
4. Which states are directionally persistent, mean-reverting, or noise/chop?
5. Which market/sector states make a target-local pattern useful or useless?
6. Does adding target state improve direction-neutral tradability/path outcomes versus market-only and market+sector baselines?

## Implementation order

1. Keep this Layer 3 target-state contract as the source of truth.
2. Keep `model_03_target_state_vector` package and tests aligned with this contract.
3. Add the `trading-data` source/feature target-state request boundary.
4. Build baseline target-state vectors from bars/liquidity plus Layer 1/2 refs.
5. Add forward state/outcome labels and market-only / sector-only baselines.
6. Only after state/outcome relationships are accepted, design downstream action/expression consumers outside Layer 3.

## Acceptance gates

A Layer 3 implementation is not accepted unless it proves:

- point-in-time construction with `available_time` and `tradeable_time` separation;
- raw ticker/company identity excluded from model-facing vectors;
- market, sector, target, and cross-state blocks are separately inspectable;
- target-state labels are future-aware only in training/evaluation, never in inference features;
- baselines compare market-only, market+sector, and market+sector+target vectors;
- state vectors improve at least one accepted direction-neutral forward path/tradability outcome relationship with split-stability evidence;
- liquidity/cost diagnostics identify states that are theoretically predictive but practically untradeable;
- audit/routing metadata can map decisions back to real symbols without leaking identity into fitting vectors;
- generated outputs, large artifacts, and credentials stay out of Git;
- Layer 4 Alpha / Confidence and Layer 5 Trading Projection consumers, not Layer 3, own direction-confidence calibration, target/stop/action projection, position sizing, and final trading instructions.
