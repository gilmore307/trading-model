# Target state vector V1 contract

Status: Draft V1 contract for review.

This file owns the model-local Layer 3 target state-vector contract. Layer 3 is not a strategy-variant selector. It constructs an anonymous, point-in-time state vector that lets later layers study which target board/tape states produce tradeable outcomes under the current market and sector context.

## Row identity

Canonical model output when promoted:

```text
trading_model.model_03_target_state_vector
```

Required identity fields:

| Field | Role |
|---|---|
| `available_time` | When all input evidence for the state row is available. |
| `tradeable_time` | Earliest realistic time a downstream decision may trade from this state. |
| `target_candidate_id` | Opaque anonymous candidate key; never a categorical fitting feature. |
| `target_state_vector_version` | Reviewed V1 contract/config version. |
| `market_context_state_ref` | Layer 1 context row reference. |
| `sector_context_state_ref` | Layer 2 context row reference. |
| `target_state_vector_ref` | Stable reference/hash for the model-facing state payload. |

Routing/audit fields such as `audit_symbol_ref` and `routing_symbol_ref` must stay outside the model-facing vector.

## V1 feature blocks

V1 has four inspectable model-facing blocks. Each block may be stored as JSONB during research, but block names and field groups must remain stable enough for tests, diagnostics, and review.

### `market_state_features`

Inherited or projected from Layer 1. Layer 3 may copy references and normalized context values, but it must not reinterpret market state with future target outcomes.

| Field group | Meaning |
|---|---|
| `market_regime_state` | Current broad market regime/state id or score bundle. |
| `market_trend_state` | Broad trend direction/strength from accepted Layer 1 factors. |
| `market_volatility_state` | Broad realized/implied/range volatility state where available. |
| `market_breadth_state` | Broad participation/breadth context when accepted by Layer 1. |
| `market_liquidity_stress_state` | Broad liquidity/stress/cost context when available. |
| `market_correlation_state` | Correlation/risk-on-risk-off background. |

### `sector_state_features`

Inherited or projected from Layer 2 for the sector/industry basket that admitted or prioritized the target.

| Field group | Meaning |
|---|---|
| `sector_context_state` | Current Layer 2 sector/industry state id or score bundle. |
| `sector_relative_strength_state` | Sector-vs-market relative strength and rotation context. |
| `sector_trend_stability_state` | Sector trend stability/chop/dispersion context. |
| `sector_volatility_state` | Sector volatility and volatility-vs-market context. |
| `sector_breadth_dispersion_state` | Sector internal participation and dispersion when available. |
| `sector_liquidity_tradability_state` | Basket liquidity/optionability/cost context when available. |

### `target_state_features`

Computed from anonymous target-local point-in-time evidence. V1 uses completed bars/quotes/trades only; no forward returns, realized PnL, or post-decision information may enter this block.

| Field group | Meaning |
|---|---|
| `target_return_shape` | Trailing return shape across reviewed short/intraday/day windows. |
| `target_trend_momentum_state` | Trend direction, slope, moving-average alignment, and momentum persistence. |
| `target_volatility_range_state` | ATR%, realized volatility, intraday range, range location, compression/expansion. |
| `target_gap_jump_state` | Opening/overnight/session gap, jump, and abnormal bar movement evidence. |
| `target_volume_activity_state` | Volume, dollar-volume, relative volume, and abnormal activity. |
| `target_liquidity_cost_state` | Spread, quote coverage, capacity, slippage proxy, and tradeability diagnostics. |
| `target_vwap_location_state` | Distance from VWAP/session anchors and mean-reversion pressure context. |
| `target_session_position_state` | Time-of-day/session-progress context for intraday state interpretation. |
| `target_data_quality_state` | Coverage, freshness, missingness, and source-quality diagnostics. |

### `cross_state_features`

Derived relationship features. These are the main reason Layer 3 exists: they describe how the target behaves relative to the market and sector instead of treating target bars in isolation.

| Field group | Meaning |
|---|---|
| `target_vs_market_strength` | Target return/trend strength relative to broad market context. |
| `target_vs_sector_strength` | Target return/trend strength relative to its admitting sector/industry context. |
| `target_vs_market_volatility` | Target volatility/range expansion relative to broad market volatility. |
| `target_vs_sector_volatility` | Target volatility/range expansion relative to sector volatility. |
| `target_market_beta_correlation` | Rolling beta/correlation to accepted market reference where enough history exists. |
| `target_sector_beta_correlation` | Rolling beta/correlation to accepted sector reference where enough history exists. |
| `sector_confirmation_state` | Whether target movement is sector-confirmed, sector-divergent, or idiosyncratic. |
| `idiosyncratic_residual_state` | Residual target movement after market/sector adjustment. |
| `relative_liquidity_cost_state` | Target tradability/cost relative to accepted sector or universe reference. |

## V1 synchronized state windows

The first contract uses a sparse, reviewable window set rather than many strategy-like parameter variants:

```text
5min, 15min, 60min, 390min
```

These windows are a synchronization contract, not merely a target-local calculation detail. `market_state_features`, `sector_state_features`, and `target_state_features` must always declare and use the same `state_observation_windows` for a row. `cross_state_features` may only compare values whose source blocks share the same window label.

Use these as state-observation windows for trailing return, volatility, volume, and relative-strength summaries. They are not strategy variants and should not multiply a variant universe. Add windows only after evidence shows a missing state relationship between accepted endpoints, and add the window to market, sector, target, and cross-state handling together.

## V1 label families

Labels are training/evaluation-only outputs. They must never be joined into inference feature vectors.

| Label family | Initial horizons | Role |
|---|---|---|
| `forward_return_distribution` | 15min, 60min, 390min | Future return distribution from the state. |
| `forward_path_risk` | 15min, 60min, 390min | MFE/MAE, chop, gap, and adverse excursion after the state. |
| `directional_persistence` | 15min, 60min, 390min | Whether direction persists after market/sector adjustment. |
| `reversion_pressure` | 15min, 60min, 390min | Whether stretched target states revert toward target/sector/market anchors. |
| `liquidity_tradability_outcome` | 15min, 60min | Whether the state remains tradeable after spreads, volume, and coverage gates. |
| `state_transition` | next accepted state row | Which target state tends to follow this state. |

## Baseline ladder

Layer 3 evaluation must compare these feature sets under identical labels and splits:

1. `market_only_baseline` — Layer 1 block only.
2. `market_sector_baseline` — Layer 1 + Layer 2 blocks.
3. `market_sector_target_vector` — Layer 1 + Layer 2 + target + cross-state blocks.

A V1 model is not accepted just because target features improve aggregate return prediction. It must show split-stable improvement for at least one reviewed forward outcome and must preserve liquidity/cost diagnostics so theoretically predictive but practically untradeable states can be identified.

## Rejection rules

Reject a state-vector build if it:

- includes raw ticker/company identity in model-facing fields;
- uses `target_candidate_id` as a categorical feature;
- includes forward returns, realized PnL, or future bar outcomes in inference features;
- mixes audit/routing metadata into the model-facing vector;
- collapses market, sector, target, and cross-state blocks into an uninspectable blob;
- emits mismatched state observation windows across market, sector, and target blocks;
- evaluates only against an all-regime aggregate without market/sector-conditioned review;
- optimizes strategy variants before state/outcome relationships are accepted.
