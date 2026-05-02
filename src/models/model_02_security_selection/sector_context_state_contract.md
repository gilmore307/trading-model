# sector_context_state V1 contract

This file owns the first `SecuritySelectionModel` V1 output contract for
`sector_context_state`. It is model-local until implementation/evaluation prove
which fields should be registered as shared terms.

## Purpose

Layer 2 answers: for each eligible sector/industry equity ETF basket, what is
its market-context-conditioned trend-stability state and inferred basket
attribute profile at `available_time`?

It does **not** answer which final stock to buy, which strategy to run, which
option contract to trade, or how much portfolio risk to allocate.

## Row identity

Planned physical artifact:

```text
trading_model.model_02_security_selection
```

Conceptual row shape:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Required key / identity fields:

| Field | Type | Role |
|---|---|---|
| `available_time` | timestamp | Point-in-time availability of the state row. |
| `sector_or_industry_symbol` | text | Eligible sector/industry equity ETF or basket symbol. |
| `model_id` | text | Stable model id, normally `security_selection_model`. |
| `model_version` | text | Version/config label that produced the row. |
| `market_context_state_ref` | text/null | Reference to the Layer 1 market-context row used for conditioning. |

`sector_or_industry_symbol` is routing/audit identity for a sector/industry ETF
basket. It is allowed in Layer 2 because Layer 2's unit of analysis is the
sector/industry basket. It must not be propagated as raw ticker identity into
anonymous target fitting vectors downstream.

## V1 output fields

### Observed behavior block

Point-in-time sector/industry behavior. These fields summarize evidence; they
are not final selection commands.

| Field | Type | Meaning |
|---|---|---|
| `relative_strength_score` | float/null | Market-relative strength of the basket using current point-in-time evidence. |
| `trend_direction_score` | float/null | Directional trend score after reviewed sign/scale handling. |
| `trend_persistence_score` | float/null | Evidence that trend behavior persists across recent windows. |
| `volatility_adjusted_trend_score` | float/null | Trend strength adjusted for realized volatility/chop. |
| `breadth_participation_score` | float/null | Breadth/participation support inside the basket or comparable sector universe. |
| `dispersion_score` | float/null | Cross-component dispersion; high dispersion weakens clean basket interpretation. |
| `market_correlation_score` | float/null | Current co-movement with broad market context. |
| `chop_score` | float/null | Sideways/noisy behavior diagnostic. Higher means less clean trend behavior. |

### Inferred attribute block

Posterior attributes inferred from evidence and market conditioning. These are
model outputs, not hand-written labels and not Layer 1 facts.

| Field | Type | Meaning |
|---|---|---|
| `growth_sensitivity_score` | float/null | Inferred sensitivity to growth/speculative market behavior. |
| `defensive_sensitivity_score` | float/null | Inferred sensitivity to defensive/risk-off behavior. |
| `cyclical_sensitivity_score` | float/null | Inferred sensitivity to cyclical/economic-activity behavior. |
| `rate_sensitivity_score` | float/null | Inferred sensitivity to rate/duration pressure. |
| `dollar_sensitivity_score` | float/null | Inferred sensitivity to dollar/liquidity pressure. |
| `commodity_sensitivity_score` | float/null | Inferred sensitivity to commodity/inflation pressure. |
| `risk_appetite_sensitivity_score` | float/null | Inferred sensitivity to broad risk appetite. |
| `attribute_certainty_score` | float/null | Stability/certainty of inferred attributes across refits/windows. |

Human-readable labels such as `growth`, `defensive`, or `cyclical` may be shown
only as post-fit interpretation derived from these scores; they are not input
truth and are not required row fields.

### Market-condition profile block

How the sector/industry basket behaves under the current Layer 1 market context.

| Field | Type | Meaning |
|---|---|---|
| `market_alignment_score` | float/null | Compatibility between current basket behavior and current market context. |
| `market_tailwind_score` | float/null | Evidence that current market context supports the basket's trend. |
| `market_headwind_score` | float/null | Evidence that current market context conflicts with the basket's trend. |
| `transition_sensitivity_score` | float/null | Sensitivity to changing/unstable market context. |
| `context_conditioned_stability_score` | float/null | Trend-stability score after conditioning on market context. |

### Trend-stability block

Core V1 output block for downstream target/strategy work.

| Field | Type | Meaning |
|---|---|---|
| `trend_stability_score` | float/null | Overall stability of tradable trend behavior. |
| `trend_certainty_score` | float/null | Confidence/certainty in the trend-stability reading. |
| `false_break_risk_score` | float/null | Risk that apparent trend behavior is a false break. |
| `reversal_risk_score` | float/null | Risk of near-term reversal under current evidence. |
| `cycle_regularity_score` | float/null | Evidence that behavior cycles regularly enough for downstream strategy use. |
| `selection_readiness_score` | float/null | Readiness for downstream anonymous target generation; not a final selection. |

### Composition / transmission block

Basket composition and `stock_etf_exposure` evidence. This block may inform
anonymous target generation later, but it must not become hidden final stock
selection.

| Field | Type | Meaning |
|---|---|---|
| `stock_etf_exposure_ref` | text/null | Reference to the point-in-time exposure artifact used for composition evidence. |
| `holding_count` | integer/null | Number of known holdings/components in the evidence snapshot. |
| `top_holding_weight` | float/null | Largest holding weight, when available. |
| `concentration_score` | float/null | Basket concentration diagnostic. Higher means more concentrated. |
| `composition_freshness_score` | float/null | Freshness/reliability of holdings and exposure evidence. |
| `composition_overlap_score` | float/null | Overlap/crowding diagnostic versus other eligible baskets. |
| `handoff_stock_universe_ref` | text/null | Optional reference to downstream candidate-universe evidence, not selected stocks. |

### Tradability block

Whether the basket can be used as a clean, liquid sector/industry context and
whether downstream stock/option work should be cautious.

| Field | Type | Meaning |
|---|---|---|
| `liquidity_score` | float/null | Basket liquidity/volume/depth diagnostic. |
| `spread_cost_score` | float/null | Estimated spread/friction burden. Higher means worse cost. |
| `optionability_score` | float/null | Option-chain availability/quality diagnostic for ETF or constituents. |
| `capacity_score` | float/null | Capacity/slippage diagnostic for using the basket context downstream. |
| `tradability_score` | float/null | Combined tradability diagnostic for downstream gating. |

### Risk / event block

Risk diagnostics used by downstream strategy, option-expression, and portfolio
risk layers.

| Field | Type | Meaning |
|---|---|---|
| `volatility_risk_score` | float/null | Realized/implied volatility risk diagnostic. |
| `gap_risk_score` | float/null | Gap/jump risk diagnostic. |
| `event_density_score` | float/null | Scheduled/unscheduled event density around the basket. |
| `abnormal_activity_score` | float/null | Equity/ETF abnormal activity diagnostic when available. |
| `correlation_stress_score` | float/null | Stress from rising market/basket correlation or contagion. |
| `downside_tail_risk_score` | float/null | Tail/downside risk diagnostic. |

### Eligibility / quality block

Whether the row is usable and why it may be excluded from downstream candidate
handoff.

| Field | Type | Meaning |
|---|---|---|
| `eligibility_state` | text | One of `eligible`, `watch`, `excluded`, or `insufficient_data`. |
| `eligibility_reason_codes` | text/null | Semicolon-separated stable reason codes for watch/excluded/insufficient rows. |
| `data_quality_score` | float/null | Input coverage/freshness/reliability summary. |
| `state_quality_score` | float/null | Overall reliability of the produced `sector_context_state` row. |
| `evidence_count` | integer/null | Count of usable evidence fields/families contributing to the row. |

## Excluded V1 fields

The following do not belong in `sector_context_state` V1:

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
3. `stock_etf_exposure` used only as composition/transmission evidence;
4. inferred attributes stable enough across chronological refits to be useful;
5. trend-stability separation versus a market-context-free baseline;
6. downstream anonymous target generation can consume the row without raw
   company/ticker identity leakage.
