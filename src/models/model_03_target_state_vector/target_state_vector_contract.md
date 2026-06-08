# Target context state contract

Status: Accepted contract; production promotion pending real-data evidence and accepted review.

This file owns the model-local Layer 3 target context/state-vector output contract. Layer 3 is not a strategy-variant selector. It constructs anonymous, point-in-time, direction-neutral `target_context_state` that lets later layers study which target board/tape states produce tradeable outcomes under the current market and sector context. It may rank the current anonymous candidate-policy batch for target handoff, but it does not emit final actions, position sizes, or option expressions.

`docs/21_vector_taxonomy.md` owns the vocabulary distinction: `anonymous_target_feature_vector` is the Layer 3 preprocessing/input vector, while `target_context_state` is the Layer 3 conceptual model output.

## Row identity

Canonical model output when promoted:

```text
trading_model.model_03_target_state_vector
```

The primary SQL table owns row identity, upstream refs, `target_context_state_ref`, and scalar `3_*` score-family outputs. Full inspectable payload blocks, embeddings, clusters, and row-quality diagnostics live in support artifacts:

```text
trading_model.model_03_target_state_vector_explainability
trading_model.model_03_target_state_vector_diagnostics
```

`state_quality_diagnostics` is promotion-review evidence, not a promotion decision field. Durable promotion state belongs to evaluation and promotion artifacts.

Required identity fields:

| Field | Role |
|---|---|
| `available_time` | When all input evidence for the state row is available. |
| `tradeable_time` | Earliest realistic time a downstream decision may trade from this state. |
| `target_candidate_id` | Opaque anonymous candidate key; never a categorical fitting feature. |
| `target_context_state_version` | Reviewed contract/config version. |
| `market_context_state_ref` | Layer 1 context row reference. |
| `sector_context_state_ref` | Layer 2 context row reference. |
| `target_context_state_ref` | Stable reference/hash for the model-facing state payload. |

Routing/audit fields such as `audit_symbol_ref` and `routing_symbol_ref` must stay outside the model-facing vector. `target_candidate_id` is row identity only and must not be used as a fitting feature.

Task execution may be target-major: one routing symbol can complete all assigned folds before the next routing symbol starts. That ordering is an implementation schedule, not a model boundary. Training/evaluation must pool anonymous target-state samples and report fold-level, candidate-policy-aware selection/ranking evidence.

## Feature Blocks

`target_context_state` has four inspectable model-facing output blocks. Each block may be stored as JSONB during research, but block names and field groups must remain stable enough for tests, diagnostics, and review. Derived embeddings/clusters may support diagnostics, but they must not replace these inspectable blocks as the primary contract.

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

Computed from anonymous target-local point-in-time evidence. The target-local block uses completed bars/quotes/trades only; no forward returns, realized PnL, or post-decision information may enter this block.

| Field group | Meaning |
|---|---|
| `target_price_state` | Current completed-bar price anchors used for path labels/evaluation; no future bars. |
| `target_direction_return_shape` | Signed current-state direction evidence and trailing return shape across reviewed short/intraday/day windows. |
| `target_trend_quality_state` | Trend direction sign, structural quality, slope, moving-average/VWAP alignment, path stability, and momentum persistence. |
| `target_trend_age_state` | Trend/state age, time since last direction flip, flip count, and persistence evidence. |
| `target_exhaustion_decay_state` | Momentum decay, volume exhaustion, volatility exhaustion, trend-slope decay, and late-trend risk evidence. |
| `target_volatility_range_state` | ATR%, realized volatility, intraday range, range location, compression/expansion, and transition-risk pressure. |
| `target_gap_jump_state` | Opening/overnight/session gap, jump, and abnormal bar movement evidence. |
| `target_volume_activity_state` | Volume, dollar-volume, relative volume, and abnormal activity. |
| `target_liquidity_tradability_state` | Spread, quote coverage, capacity, slippage proxy, borrow/shortability where applicable, and tradeability diagnostics. |
| `target_vwap_location_state` | Distance from VWAP/session anchors and mean-reversion pressure context. |
| `target_session_position_state` | Time-of-day/session-progress context for intraday state interpretation: minutes since open/to close, session phase, opening/midday/closing flags, distance to open/VWAP, and range position. |
| `target_peer_rank_state` | Cross-sectional ranks inside the point-in-time peer/candidate pool for tradability qualities, not raw strength. |
| `target_shortability_state` | Optional shortability/borrow/locate evidence; may be null until a reviewed source exists and must not imply position sizing. |
| `target_option_chain_state` | Optional ThetaData-derived, target-level option-chain environment state. It summarizes chain liquidity, IV pressure, skew pressure, term-structure pressure, and option activity pressure without exposing contract identity or executable option terms. |
| `target_event_risk_state` | Optional scheduled/news/halt/macro event-risk overlay evidence; may be null until reviewed event sources exist. |
| `target_data_quality_state` | Coverage, freshness, missingness, and source-quality diagnostics. |

Opaque unresolved source/feature mapping identifiers retained for future review: `/implied/range`, `/stress/cost`, `/optionability/cost`. Do not rewrite these identifiers or infer provider semantics until the corresponding source contracts are reviewed.

#### `target_option_chain_state`

When option context is present, Layer 3 uses ThetaData as the canonical option market-data source and reduces a bounded source envelope into anonymous target-level state through deterministic role selection. The reduction answers what the target's option market environment looks like; it must not identify a contract, expiry, strike, premium, quote, or option order candidate. The source-side acquisition envelope is bounded by `max_dte=180` and a narrow strike range; the model-facing contract is the role selector, not the provider request itself.

Canonical stable-core expiry buckets:

| Bucket | DTE range | Layer 3 use |
|---|---:|---|
| `front` | 7-45 | Canonical state. |
| `near` | 46-90 | Canonical state. |
| `mid` | 91-180 | Canonical state. |

Canonical selector roles:

| Role | Definition |
|---|---|
| `atm` | Nearest strike to spot with usable quote/IV evidence, preferring `abs(delta)` from `0.45` through `0.55` when delta quality is available. |
| `canonical_call_wing` | Preferred call wing near 25-delta, falling back to roughly 5% OTM moneyness. |
| `canonical_put_wing` | Preferred put wing near 25-delta, falling back to roughly 5% OTM moneyness. |
| `round_activity_attention` | Round strike near spot as point-in-time attention evidence. |
| `oi_activity_attention` | Point-in-time open-interest attention candidate when OI is observable. |
| `short_expiry_pressure_overlay` | Separate `0-6 DTE` ATM/activity pressure state, not part of stable structural core. |

The model-facing option state groups are:

| State group | Contract definition |
|---|---|
| `target_option_liquidity_state` | Robust target-level option liquidity/tradability condition from valid quote spread, depth, volume, open interest, and quote quality across eligible buckets. It may emit normalized states such as `thin`, `normal`, `deep`, or `stressed`, not best contract details. |
| `target_iv_pressure_state` | Front ATM IV pressure from a capped, quote-quality/liquidity-weighted robust median of eligible ATM front-bucket IV observations, normalized against the target's rolling baseline. It must not emit raw single-contract IV. |
| `target_option_skew_pressure_state` | Put/call skew from eligible 25-delta put IV minus 25-delta call IV inside matching expiry buckets, reduced to target-level pressure states such as `balanced`, `put_skew`, `call_skew`, or `extreme_put_skew`. |
| `target_option_term_structure_pressure_state` | Cross-expiry ATM IV slope/richness such as front-vs-near and near-vs-mid pressure. If fewer than two canonical buckets have reliable coverage, term-structure state is missing and diagnostics record why. |
| `target_option_flow_pressure_state` | Target-level option activity pressure from point-in-time activity attention roles and observable open interest where available, normalized against the target's rolling baseline. Same-snapshot volume, trade count, and notional may support state measurement or validation but must not be used as prefetch selector inputs. It must use neutral wording such as `call_activity_elevated` or `put_activity_elevated`, not alpha claims. |
| `target_short_expiry_pressure_overlay` | Separate `0-6 DTE` ATM/activity pressure state. It may support short-horizon pressure interpretation but must not be merged into stable structural core. |

Coverage, missingness, source provenance, snapshot refs, raw bucket counts, and fields such as `option_quote_available_ratio`, `option_trade_available_ratio`, `option_iv_available_ratio`, `option_greeks_available_ratio`, `option_chain_observability_score`, and `option_liquidity_quality_score` belong in diagnostics or receipts. They are not Layer 3 model-facing output state.

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

## Synchronized State Windows

The first contract uses a sparse, reviewable window set rather than many strategy-like parameter variants:

```text
10min, 1h, 1D, 1W
```

These windows are a synchronization contract, not merely a target-local calculation detail. `market_state_features`, `sector_state_features`, and `target_state_features` must always declare and use the same `state_observation_windows` for a row. `cross_state_features` may only compare values whose source blocks share the same window label.

Use these as state-observation windows for trailing return, volatility, volume, and relative-strength summaries. They are not downstream action variants and should not multiply a variant universe. Add windows only after evidence shows a missing state relationship between accepted endpoints, and add the window to market, sector, target, and cross-state handling together.

## Direction-neutral score families

Layer 3 outputs may include scalar summaries inside block payloads, but these score families must not be conflated:

| Score family | Range | Contract meaning |
|---|---|---|
| `3_target_direction_score_<window>` | [-1, 1] | Signed current-state direction evidence. Positive/negative are long/short state signs, not quality and not position. |
| `3_target_direction_strength_score_<window>` | [0, 1] | Absolute current direction evidence strength. High can describe either clean long or clean short state evidence. |
| `3_target_trend_quality_score_<window>` | [0, 1] | Clarity/structure of the target trend state independent of sign. |
| `3_target_path_stability_score_<window>` | [0, 1] | Smoothness and persistence of the state path; higher means fewer whipsaws. |
| `3_target_noise_score_<window>` | [0, 1] | Bar-to-bar chop, wick/noise, abnormal jumps, and execution-disruptive path noise. Higher means worse noise. |
| `3_target_transition_risk_score_<window>` | [0, 1] | Risk that current state is switching, decaying, crowded, or otherwise fragile. Higher means more risk. |
| `3_target_state_persistence_score_<window>` | [0, 1] | Direction-neutral persistence/age support for the current state, separate from direction sign. |
| `3_target_exhaustion_risk_score_<window>` | [0, 1] | Direction-neutral late-trend/exhaustion/decay risk. Higher means worse risk. |
| `3_target_liquidity_tradability_score` | [0, 1] | Liquidity/spread/capacity/borrow support for practical execution. |
| `3_option_liquidity_score` | [0, 1] | Target-level option-chain liquidity condition reduced from allowed option liquidity state. Higher means cleaner option market liquidity. |
| `3_option_observability_score` | [0, 1] | Completeness of accepted target-level option state groups. It is not a source receipt, snapshot ref, or raw coverage field. |
| `3_option_iv_pressure_score` | [0, 1] | Target-level front ATM IV pressure state. Higher means more elevated option IV pressure. |
| `3_option_signed_skew_pressure_score` | [-1, 1] | Signed target-level option skew pressure: positive for put-skew pressure, negative for call-skew pressure, zero for balanced. |
| `3_option_term_structure_pressure_score` | [0, 1] | Target-level option term-structure pressure. Higher means front/near IV richness pressure. |
| `3_option_signed_flow_pressure_score` | [-1, 1] | Signed target-level option activity pressure: positive for call activity, negative for put activity, zero for balanced. |
| `3_context_direction_alignment_score_<window>` | [-1, 1] | Signed target/sector/market direction alignment. |
| `3_context_support_quality_score_<window>` | [0, 1] | Direction-neutral support quality from sector/market/peer context. |
| `3_tradability_score_<window>` | [0, 1] | Direction-neutral state tradability. Stable short states can score highly. It combines direction strength, trend quality, path stability, context support, liquidity, persistence, data quality, and inverted noise/transition/exhaustion risk; it must never mean “suitable long.” |
| `3_state_quality_score` | [0, 1] | Reliability/completeness of the produced state vector, not opportunity. |
| `3_target_handoff_state` | text | Candidate-policy batch handoff value: `selected`, `watch`, `blocked`, or `insufficient_data`. |
| `3_target_handoff_bias` | text | Candidate-policy batch bias value: `long_bias`, `short_bias`, `neutral`, or `mixed`; separate from handoff state. |
| `3_target_handoff_rank` | integer/null | Rank inside the candidate-policy batch. It is not a portfolio weight. |
| `3_target_selection_reason_codes` | text/null | Stable reason codes for target selected/watch/blocked/insufficient-data outcomes. |

`3_target_direction_score_<window>` is not Layer 5 alpha/direction confidence. Event context, direction-confidence calibration, target/stop/action projection, and position sizing belong to downstream consumers.

## Label Families

Labels are training/evaluation-only outputs. They must never be joined into inference feature vectors. If a signed label uses direction orientation, the orientation must come from deterministic point-in-time state evidence or an out-of-sample upstream prediction, never from the same fitted target being evaluated. The accepted Layer 3 training route uses completed 1-minute source rows to form multi-frame state features, then evaluates future path quality, tradability preservation, and state transition behavior over the label horizon.

| Label family | Initial horizons | Role |
|---|---|---|
| `signed_forward_return_distribution` | 10min, 1h, 1D, 1W | Direction-neutral future return distribution using deterministic point-in-time orientation, not fitted alpha confidence. |
| `future_tradeable_path` | 10min, 1h, 1D, 1W | Direction-oriented future path quality from path efficiency, MFE/MAE balance, and sign-flip penalty. |
| `forward_path_risk` | 10min, 1h, 1D, 1W | MFE/MAE, chop, sign flips, gap, and adverse excursion after the state. |
| `directional_persistence` | 10min, 1h, 1D, 1W | Whether direction persists after market/sector adjustment. |
| `reversion_pressure` | 10min, 1h, 1D, 1W | Whether stretched target states revert toward target/sector/market anchors. |
| `liquidity_tradability_outcome` | 10min, 1h, 1D | Whether the state remains tradeable after spreads, volume, and coverage gates. |
| `state_transition_quality` | 10min, 1h, 1D, 1W | Whether the future state preserves or cleanly transitions from the current state without noisy sign flips. |
| `candidate_policy_rank_outcome` | 10min, 1h, 1D, 1W | Whether selected/top-ranked anonymous candidates outperform watch/blocked/control candidates on path quality and liquidity-adjusted tradability inside a fixed candidate-universe policy batch. |

## Baseline ladder

Layer 3 evaluation must compare these feature sets under identical labels and splits:

1. `market_only_baseline` — Layer 1 block only.
2. `market_sector_baseline` — Layer 1 + Layer 2 blocks.
3. `market_sector_target_context` — Layer 1 + Layer 2 + target + cross-state blocks.

A model is not accepted just because target features improve aggregate return prediction or long-only outcomes. It must show split-stable improvement for at least one reviewed direction-neutral forward path/tradability outcome and must preserve liquidity/cost diagnostics so theoretically predictive but practically untradeable states can be identified. Preferred tradability validation buckets compare `3_tradability_score_<window>` against MFE/MAE balance, path efficiency, first-target-before-stop behavior, direction flip count, state-transition rate, and spread/liquidity degradation rather than only forward return. Selection validation must also compare selected/top-N targets with watch/blocked/control candidates inside the same candidate-universe policy batch.

## Rejection rules

Reject a state-vector build if it:

- includes raw ticker/company identity in model-facing fields;
- uses `target_candidate_id` as a categorical feature;
- includes forward returns, realized PnL, or future bar outcomes in inference features;
- mixes audit/routing metadata into the model-facing vector;
- emits option contract identity or executable option-chain details such as `option_contract_id`, OCC symbol, strike, expiry, DTE, delta/Greeks, premium, quote, bid/ask, raw single-contract IV, or `option_chain_snapshot_ref`;
- collapses market, sector, target, and cross-state blocks into an uninspectable blob;
- emits mismatched state observation windows across market, sector, and target blocks;
- evaluates only against an all-regime aggregate without market/sector-conditioned and long-bias/short-bias review;
- optimizes downstream action variants before state/outcome relationships are accepted;
- treats positive direction as inherently better than negative direction;
- trains Layer 4/5/6 consumers on in-sample fitted direction-confidence outputs from Layer 3.
