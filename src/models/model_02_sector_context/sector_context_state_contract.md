# sector_context_state V1 contract

This file owns the first `SectorContextModel` V1 output contract for `sector_context_state`. It is model-local until implementation/evaluation prove which fields should be registered as shared terms.

## Purpose

Layer 2 answers: for each eligible sector/industry equity ETF basket, what is its market-context-conditioned trend-stability state and inferred basket attribute profile at `available_time`?

It may mark which sector/industry baskets are suitable for downstream candidate construction. It does **not** answer which final stock to buy, which strategy to run, which option contract to trade, or how much portfolio risk to allocate.

## Physical artifacts

Layer 2 uses three physical artifacts so the downstream contract stays narrow without discarding review and gating evidence:

```text
trading_model.model_02_sector_context                  # output
trading_model.model_02_sector_context_explainability   # explainability
trading_model.model_02_sector_context_diagnostics      # diagnostics
```

`model_02_sector_context` is the stable downstream dependency surface. `model_02_sector_context_explainability` is for human review/debug/explain. `model_02_sector_context_diagnostics` is for acceptance, monitoring, and gating.

Downstream production logic should not hard-depend on explainability or diagnostics fields without a later reviewed promotion decision.

## Row identity

Conceptual row shape:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Required key / identity fields:

| Field | Type | Role |
|---|---|---|
| `available_time` | timestamp | Point-in-time availability of the state row. |
| `sector_or_industry_symbol` | text | Eligible sector/industry equity ETF or basket symbol. |
| `model_id` | text | Stable model id, normally `sector_context_model`. |
| `model_version` | text | Version/config label that produced the row. |
| `market_context_state_ref` | text/null | Reference to the Layer 1 market-context row used only as conditioning context. |

Layer 2 model fields use compact `2_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading identifiers where required rather than storing semantic aliases such as `layer02_*`.

Layer 2 must not copy Layer 1 market-property factor names into ETF style fields. Layer 1 provides the background condition used to compare similar market environments; Layer 2 outputs a separate conditional behavior vector learned from each ETF/basket's behavior under those environments.

`sector_or_industry_symbol` is routing/audit identity for a sector/industry ETF basket. It is allowed in Layer 2 because Layer 2's unit of analysis is the sector/industry basket. It must not be propagated as raw ticker identity into anonymous target fitting vectors downstream.

## `model_02_sector_context` output fields

The primary output is intentionally narrow: identity, trend/context stability state, downstream sector handoff, and eligibility/quality summary.

### Trend-stability state

| Field | Type | Meaning |
|---|---|---|
| `2_trend_stability_score` | float/null | Overall stability of tradable trend behavior. |
| `2_trend_certainty_score` | float/null | Confidence/certainty in the trend-stability reading. |
| `2_context_conditioned_stability_score` | float/null | Trend-stability score after conditioning on market context. |
| `2_selection_readiness_score` | float/null | Readiness for downstream anonymous target generation; not a final selection. |

### Downstream sector handoff

Layer 2 may identify sector/industry baskets suitable for downstream anonymous target construction. It does not use ETF holdings to choose stocks. ETF holdings and `stock_etf_exposure` belong to the downstream candidate builder / Layer 3 input-preparation boundary.

| Field | Type | Meaning |
|---|---|---|
| `2_sector_handoff_state` | text/null | One of `selected`, `watch`, `blocked`, or `insufficient_data`. |
| `2_sector_handoff_rank` | integer/null | Optional rank among sector/industry baskets for candidate-builder priority; not a portfolio weight. |
| `2_sector_handoff_reason_codes` | text/null | Stable reason codes explaining why the basket is selected, watched, or blocked. |

### Eligibility / quality summary

| Field | Type | Meaning |
|---|---|---|
| `2_eligibility_state` | text | One of `eligible`, `watch`, `excluded`, or `insufficient_data`. |
| `2_eligibility_reason_codes` | text/null | Semicolon-separated stable reason codes for watch/excluded/insufficient rows. |
| `2_state_quality_score` | float/null | Overall reliability of the produced `sector_context_state` row. |
| `2_evidence_count` | integer/null | Count of usable evidence fields/families contributing to the row. |

## `model_02_sector_context_explainability` fields

Explainability owns behavior and attribution detail for human review. These fields are allowed to be wider and more detailed than the primary output, but they should not become hard downstream dependencies.

### Observed behavior block

| Field | Type | Meaning |
|---|---|---|
| `2_relative_strength_score` | float/null | Market-relative strength of the basket using current point-in-time evidence. |
| `2_trend_direction_score` | float/null | Directional trend score after reviewed sign/scale handling. |
| `2_trend_persistence_score` | float/null | Evidence that trend behavior persists across recent windows. |
| `2_volatility_adjusted_trend_score` | float/null | Trend strength adjusted for realized volatility/chop. |
| `2_breadth_participation_score` | float/null | Breadth/participation support inside the basket or comparable sector universe. |
| `2_dispersion_score` | float/null | Cross-component dispersion; high dispersion weakens clean basket interpretation. |
| `2_market_correlation_score` | float/null | Current co-movement with broad market context. |
| `2_chop_score` | float/null | Sideways/noisy behavior diagnostic. Higher means less clean trend behavior. |

### Inferred attribute block

Posterior attributes are model outputs, not hand-written labels and not Layer 1 facts.

| Field | Type | Meaning |
|---|---|---|
| `2_growth_sensitivity_score` | float/null | Inferred sensitivity to growth/speculative market behavior. |
| `2_defensive_sensitivity_score` | float/null | Inferred sensitivity to defensive/risk-off behavior. |
| `2_cyclical_sensitivity_score` | float/null | Inferred sensitivity to cyclical/economic-activity behavior. |
| `2_rate_sensitivity_score` | float/null | Inferred sensitivity to rate/duration pressure. |
| `2_dollar_sensitivity_score` | float/null | Inferred sensitivity to dollar/liquidity pressure. |
| `2_commodity_sensitivity_score` | float/null | Inferred sensitivity to commodity/inflation pressure. |
| `2_risk_appetite_sensitivity_score` | float/null | Inferred sensitivity to broad risk appetite. |
| `2_attribute_certainty_score` | float/null | Stability/certainty of inferred attributes across refits/windows. |

Human-readable labels such as `growth`, `defensive`, or `cyclical` may be shown only as post-fit interpretation derived from these scores; they are not input truth and are not required row fields.

### Conditional behavior block

These fields describe how the sector/industry basket behaves under similar Layer 1 market backgrounds. They are ETF/basket behavior properties, not reused Layer 1 market-property factors.

V1 prefers signed axes over duplicated opposite fields. Positive and negative values describe opposite behavior on the same reviewed axis; magnitude describes strength.

| Field | Type | Meaning |
|---|---|---|
| `2_conditional_beta_score` | float/null | Relative market beta under similar market-context rows. |
| `2_directional_coupling_score` | float/null | Signed direction coupling: positive = moves with broad market direction; negative = inverse behavior. |
| `2_volatility_response_score` | float/null | Signed volatility response: positive = amplifies broad-market volatility; negative = dampens it. |
| `2_capture_asymmetry_score` | float/null | Signed conditional capture: positive = upside-favorable capture; negative = downside-heavy capture. |
| `2_response_convexity_score` | float/null | Signed nonlinear response: positive = favorable convexity; negative = adverse concavity. |
| `2_context_support_score` | float/null | Signed current-context support: positive = tailwind; negative = headwind. |
| `2_transition_sensitivity_score` | float/null | Sensitivity to changing/unstable market context. |

### Reason and evidence detail

Explainability may also include contributing evidence refs, reason-code expansions, bucket/subscore detail, config refs, and feature-family contribution detail once implementation proves the concrete shape.

## `model_02_sector_context_diagnostics` fields

Diagnostics owns acceptance, monitoring, and gating evidence. These fields may gate use of the row, but they do not directly express the sector-context state itself.

### Tradability diagnostics

| Field | Type | Meaning |
|---|---|---|
| `2_liquidity_score` | float/null | Basket liquidity/volume/depth diagnostic. |
| `2_spread_cost_score` | float/null | Estimated spread/friction burden. Higher means worse cost. |
| `2_optionability_score` | float/null | Option-chain availability/quality diagnostic for ETF or constituents. |
| `2_capacity_score` | float/null | Capacity/slippage diagnostic for using the basket context downstream. |
| `2_tradability_score` | float/null | Combined tradability diagnostic for downstream gating. |

### Risk / event diagnostics

| Field | Type | Meaning |
|---|---|---|
| `2_volatility_risk_score` | float/null | Realized/implied volatility risk diagnostic. |
| `2_gap_risk_score` | float/null | Gap/jump risk diagnostic. |
| `2_event_density_score` | float/null | Scheduled/unscheduled event density around the basket. |
| `2_abnormal_activity_score` | float/null | Equity/ETF abnormal activity diagnostic when available. |
| `2_correlation_stress_score` | float/null | Stress from rising market/basket correlation or contagion. |
| `2_downside_tail_risk_score` | float/null | Tail/downside risk diagnostic. |

### Data and model diagnostics

| Field | Type | Meaning |
|---|---|---|
| `2_data_quality_score` | float/null | Input coverage/freshness/reliability summary. |

Diagnostics may also include coverage/freshness/missingness detail, baseline comparison, rolling/refit stability, chronological split evidence, and no-future-leak checks once implementation proves the concrete shape.

## Excluded V1 fields

The following do not belong in `sector_context_state` V1:

- ETF holdings-derived stock-universe membership;
- `stock_etf_exposure` rows or stock exposure scores;
- final selected stock symbols;
- final stock weights;
- final ETF/sector allocation weights;
- entry time, entry price, stop, target, or holding-period instruction;
- strategy family choice or strategy parameters;
- option contract, DTE, delta, strike, premium, or Greeks selection;
- portfolio size, exposure, execution policy, or kill-switch instruction;
- future returns or realized PnL;
- hand-written sector labels used as input truth.

## Evaluation requirements

V1 acceptance must show:

1. point-in-time construction with no future labels in production fields;
2. eligible baskets limited to reviewed sector/industry equity ETFs;
3. ETF holdings and `stock_etf_exposure` are not used as Layer 2 core behavior-model inputs;
4. inferred attributes stable enough across chronological refits to be useful;
5. trend-stability separation versus a market-context-free baseline;
6. downstream anonymous target generation can consume selected Layer 2 baskets, use holdings/exposure evidence to build stock candidates, and then anonymize candidates without raw company/ticker identity leakage in strategy fitting.
