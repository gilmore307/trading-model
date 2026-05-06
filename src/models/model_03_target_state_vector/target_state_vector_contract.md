# Target state vector V1 contract

Status: Accepted V1 contract; deterministic implementation/evaluation scaffold complete; production promotion pending real-data evidence and accepted review.

This file owns the model-local Layer 3 target state-vector output contract. Layer 3 is not a strategy-variant selector. It constructs an anonymous, point-in-time, direction-neutral tradability state vector that lets later layers study which target board/tape states produce tradeable outcomes under the current market and sector context.

`docs/92_vector_taxonomy.md` owns the vocabulary distinction: `anonymous_target_feature_vector` is the Layer 3 preprocessing/input vector, while `target_state_vector` is the Layer 3 model output.

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

Routing/audit fields such as `audit_symbol_ref` and `routing_symbol_ref` must stay outside the model-facing vector. `target_candidate_id` is row identity only and must not be used as a fitting feature.

## V1 feature blocks

V1 `target_state_vector` has four inspectable model-facing output blocks. Each block may be stored as JSONB during research, but block names and field groups must remain stable enough for tests, diagnostics, and review. Derived embeddings/clusters may support diagnostics, but they must not replace these inspectable blocks as the primary contract.

### `market_state_features`

Inherited or projected from Layer 1. Layer 3 may copy references and normalized context values, but it must not reinterpret market state with future target outcomes.

| Field group | Meaning |
|---|---|
| `market_regime_state` | Current broad market regime/state id or score bundle. |
| `market_trend_state` | Broad trend direction, trend quality, and transition-risk context from accepted Layer 1 factors. |
| `market_volatility_state` | Broad realized/implied/range volatility state where available. |
| `market_breadth_state` | Broad participation/breadth context when accepted by Layer 1. |
| `market_liquidity_stress_state` | Broad liquidity/stress/cost context when available. |
| `market_correlation_state` | Correlation/risk-on-risk-off background. |

### `sector_state_features`

Inherited or projected from Layer 2 for the sector/industry basket that admitted or prioritized the target.

| Field group | Meaning |
|---|---|
| `sector_context_state` | Current Layer 2 sector/industry state id or score bundle. |
| `sector_relative_direction_state` | Signed sector-vs-market direction evidence and handoff bias from accepted Layer 2 state. |
| `sector_trend_quality_stability_state` | Sector trend quality, stability, chop/noise, and transition-risk context. |
| `sector_volatility_state` | Sector volatility and volatility-vs-market context. |
| `sector_breadth_dispersion_state` | Sector internal participation and dispersion when available. |
| `sector_liquidity_tradability_state` | Basket liquidity/optionability/cost context when available. |

### `target_state_features`

Computed from anonymous target-local point-in-time evidence. V1 uses completed bars/quotes/trades only; no forward returns, realized PnL, or post-decision information may enter this block.

| Field group | Meaning |
|---|---|
| `target_direction_return_shape` | Signed current-state direction evidence and trailing return shape across reviewed short/intraday/day windows. |
| `target_trend_quality_state` | Trend direction sign, structural quality, slope, moving-average/VWAP alignment, and momentum persistence. |
| `target_volatility_range_state` | ATR%, realized volatility, intraday range, range location, compression/expansion, and transition-risk pressure. |
| `target_gap_jump_state` | Opening/overnight/session gap, jump, and abnormal bar movement evidence. |
| `target_volume_activity_state` | Volume, dollar-volume, relative volume, and abnormal activity. |
| `target_liquidity_tradability_state` | Spread, quote coverage, capacity, slippage proxy, borrow/shortability where applicable, and tradeability diagnostics. |
| `target_vwap_location_state` | Distance from VWAP/session anchors and mean-reversion pressure context. |
| `target_session_position_state` | Time-of-day/session-progress context for intraday state interpretation. |
| `target_data_quality_state` | Coverage, freshness, missingness, and source-quality diagnostics. |

### `cross_state_features`

Derived relationship features. These are the main reason Layer 3 exists: they describe how the target behaves relative to the market and sector instead of treating target bars in isolation.

| Field group | Meaning |
|---|---|
| `target_vs_market_residual_direction` | Beta-adjusted target direction/residual behavior relative to broad market context. |
| `target_vs_sector_residual_direction` | Beta-adjusted target direction/residual behavior relative to admitting sector/industry context. |
| `target_vs_market_volatility` | Target volatility/range expansion relative to broad market volatility. |
| `target_vs_sector_volatility` | Target volatility/range expansion relative to sector volatility. |
| `target_market_beta_correlation` | Rolling beta/correlation to accepted market reference where enough history exists. |
| `target_sector_beta_correlation` | Rolling beta/correlation to accepted sector reference where enough history exists. |
| `sector_confirmation_state` | Whether target movement is sector-confirmed, sector-divergent, or idiosyncratic; keep signed direction alignment separate from support quality. |
| `idiosyncratic_residual_state` | Residual target movement after market/sector adjustment. |
| `relative_liquidity_tradability_state` | Target tradability/cost relative to accepted sector or universe reference. |

## V1 synchronized state windows

The first contract uses a sparse, reviewable window set rather than many strategy-like parameter variants:

```text
5min, 15min, 60min, 390min
```

These windows are a synchronization contract, not merely a target-local calculation detail. `market_state_features`, `sector_state_features`, and `target_state_features` must always declare and use the same `state_observation_windows` for a row. `cross_state_features` may only compare values whose source blocks share the same window label.

Use these as state-observation windows for trailing return, volatility, volume, and relative-strength summaries. They are not downstream action variants and should not multiply a variant universe. Add windows only after evidence shows a missing state relationship between accepted endpoints, and add the window to market, sector, target, and cross-state handling together.

## Direction-neutral score families

Layer 3 outputs may include scalar summaries inside block payloads, but these score families must not be conflated:

| Score family | Range | Contract meaning |
|---|---|---|
| `3_target_direction_score_<window>` | [-1, 1] | Signed current-state direction evidence. Positive/negative are long/short state signs, not quality and not position. |
| `3_target_trend_quality_score_<window>` | [0, 1] | Clarity/structure of the target trend state independent of sign. |
| `3_target_path_stability_score_<window>` | [0, 1] | Smoothness and persistence of the state path; higher means fewer whipsaws. |
| `3_target_noise_score_<window>` | [0, 1] | Bar-to-bar chop, wick/noise, abnormal jumps, and execution-disruptive path noise. Higher means worse noise. |
| `3_target_transition_risk_score_<window>` | [0, 1] | Risk that current state is switching, decaying, crowded, or otherwise fragile. Higher means more risk. |
| `3_target_liquidity_tradability_score` | [0, 1] | Liquidity/spread/capacity/borrow support for practical execution. |
| `3_context_direction_alignment_score_<window>` | [-1, 1] | Signed target/sector/market direction alignment. |
| `3_context_support_quality_score_<window>` | [0, 1] | Direction-neutral support quality from sector/market/peer context. |
| `3_tradability_score_<window>` | [0, 1] | Direction-neutral state tradability. Stable short states can score highly. |
| `3_state_quality_score` | [0, 1] | Reliability/completeness of the produced state vector, not opportunity. |

`3_target_direction_score_<window>` is not Layer 4 alpha/direction confidence. Direction-confidence calibration, target/stop/action projection, and position sizing belong to downstream consumers.

## V1 label families

Labels are training/evaluation-only outputs. They must never be joined into inference feature vectors. If a signed label uses direction orientation, the orientation must come from deterministic point-in-time state evidence or an out-of-sample upstream prediction, never from the same fitted target being evaluated.

| Label family | Initial horizons | Role |
|---|---|---|
| `signed_forward_return_distribution` | 15min, 60min, 390min | Direction-neutral future return distribution using deterministic point-in-time orientation, not fitted alpha confidence. |
| `forward_path_risk` | 15min, 60min, 390min | MFE/MAE, chop, sign flips, gap, and adverse excursion after the state. |
| `directional_persistence` | 15min, 60min, 390min | Whether direction persists after market/sector adjustment. |
| `reversion_pressure` | 15min, 60min, 390min | Whether stretched target states revert toward target/sector/market anchors. |
| `liquidity_tradability_outcome` | 15min, 60min | Whether the state remains tradeable after spreads, volume, and coverage gates. |
| `state_transition` | next accepted state row | Which target state tends to follow this state. |

## Baseline ladder

Layer 3 evaluation must compare these feature sets under identical labels and splits:

1. `market_only_baseline` — Layer 1 block only.
2. `market_sector_baseline` — Layer 1 + Layer 2 blocks.
3. `market_sector_target_vector` — Layer 1 + Layer 2 + target + cross-state blocks.

A V1 model is not accepted just because target features improve aggregate return prediction or long-only outcomes. It must show split-stable improvement for at least one reviewed direction-neutral forward path/tradability outcome and must preserve liquidity/cost diagnostics so theoretically predictive but practically untradeable states can be identified.

## Rejection rules

Reject a state-vector build if it:

- includes raw ticker/company identity in model-facing fields;
- uses `target_candidate_id` as a categorical feature;
- includes forward returns, realized PnL, or future bar outcomes in inference features;
- mixes audit/routing metadata into the model-facing vector;
- collapses market, sector, target, and cross-state blocks into an uninspectable blob;
- emits mismatched state observation windows across market, sector, and target blocks;
- evaluates only against an all-regime aggregate without market/sector-conditioned and long-bias/short-bias review;
- optimizes downstream action variants before state/outcome relationships are accepted;
- treats positive direction as inherently better than negative direction;
- trains Layer 4/5 consumers on in-sample fitted direction-confidence outputs from Layer 3.
