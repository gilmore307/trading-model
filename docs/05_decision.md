# Decisions

This file records the current accepted decisions for `trading-model`. Historical route changes remain in Git history; this file describes the live architecture directly.

## D001 - Repository boundary

Date: 2026-04-25
Status: Accepted

`trading-model` owns offline modeling research, validation, model-local outputs, promotion evidence, and decision-record prototypes for the trading decision stack.

It does not own raw source acquisition, global registry authority, durable storage policy, scheduling/lifecycle routing, live/paper order placement, broker/account mutation, dashboards, secrets, or committed generated runtime artifacts.

Cross-repository names, shared fields, artifact types, statuses, templates, and contracts must be routed through `trading-manager` before other repositories depend on them.

## D002 - Seven-layer model stack

Date: 2026-04-27
Status: Accepted

`trading-model` is the offline modeling home for seven layers:

| Layer | Model | Stable id | Role |
|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | Broad market context state. |
| 2 | `SecuritySelectionModel` | `security_selection_model` | Market-state-conditioned sector/industry trend-stability state. |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | Strategy fit for anonymized target candidates. |
| 4 | `TradeQualityModel` | `trade_quality_model` | Trade outcome quality, target/stop, MFE/MAE, and horizon. |
| 5 | `OptionExpressionModel` | `option_expression_model` | Stock/ETF/long-call/long-put expression and option contract constraints. |
| 6 | `EventOverlayModel` | `event_overlay_model` | Scheduled/breaking event risk and opportunity overlay across earlier layers and risk. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | Final offline portfolio risk, sizing, execution-style, exit, and kill-switch gate. |

Layer 6 is an overlay. Layer 7 may model execution-gate policy, but live/paper order placement remains outside this repository and the layer must not be renamed `ExecutionModel`.

## D003 - Current structure separates market, sector, and target work

Date: 2026-05-02
Status: Accepted

The current route is:

```text
MarketRegimeModel
  -> market_context_state

SecuritySelectionModel
  -> sector_context_state

anonymous target candidate builder + StrategySelectionModel
  -> target_candidate_id
  -> anonymous_target_feature_vector
  -> strategy_fit_state

TradeQualityModel
  -> trade_quality_state

OptionExpressionModel
  -> expression_state

EventOverlayModel
  -> event_overlay_state

PortfolioRiskModel
  -> portfolio_risk_state / final offline risk gate
```

Hard separation rules:

- Layer 1 describes broad market state only.
- Layer 2 describes sector/industry basket behavior under broad market state.
- Layer 3 is the first strategy-aware target layer.
- Final target/security choice must be strategy-aware.
- Model-facing fitting rows for target work must anonymize ticker/company identity.
- Real symbols may remain in audit/routing metadata and decision records, but not in model-facing identity features.

## D004 - Layer 1 output is market context, not selection

Date: 2026-05-01
Status: Accepted

`MarketRegimeModel` V1 outputs a continuous point-in-time broad market-property vector keyed by `available_time`.

The physical output table is:

```text
trading_model.model_01_market_regime
```

The downstream conceptual view is:

```text
market_context_state
```

Current factor fields:

```text
price_behavior_factor
trend_certainty_factor
capital_flow_factor
sentiment_factor
valuation_pressure_factor
fundamental_strength_factor
macro_environment_factor
market_structure_factor
risk_stress_factor
transition_pressure
data_quality_score
```

Layer 1 must not output sector rankings, ETF rankings, stock candidates, strategy labels, or pre-assigned ETF/sector behavior classes.

ETF/sector labels such as `growth`, `defensive`, `cyclical`, `inflation_sensitive`, or `safe_haven` are not Layer 1 facts. If useful, they are Layer 2 posterior interpretations inferred from point-in-time behavior, holdings, and market-state-conditioned trend stability.

## D005 - Layer 1 evidence and evaluation maturation

Date: 2026-05-02
Status: Accepted

Layer 1 structure is settled for V1. Remaining Layer 1 work is evidence and evaluation maturation, not boundary redesign.

For each market-property factor, maintain `src/models/model_01_market_regime/evidence_map.md` as the feature-to-factor evidence map classifying feature families as:

- primary evidence;
- diagnostic evidence;
- quality evidence;
- evaluation-only evidence;
- intentionally unused evidence.

Layer 1 evaluation must test:

- point-in-time correctness;
- rolling/expanding stability;
- responsiveness to real market transitions;
- explanatory value for Layer 2 sector trend-stability calibration;
- usefulness for `OptionExpressionModel` contract constraints;
- usefulness for `PortfolioRiskModel` risk, sizing, execution-style, exit, and kill-switch policy.

A `market_context_state` alias/view may wrap the current factor columns for downstream readability without changing the core physical fields.

## D006 - Layer 2 is sector/industry trend-stability, not final stock selection

Date: 2026-05-02
Status: Accepted

`SecuritySelectionModel` V1 outputs a sector/industry context state. It studies which sector/industry ETF baskets have stable, tradable trend behavior under each broad market context.

Layer 1 market-property factors are conditioning context only. Layer 2 must learn a separate conditional behavior vector for each ETF/basket under similar market backgrounds; it must not reuse Layer 1 factor names as ETF style fields.

Conditional behavior fields should prefer signed axes over duplicated opposite fields: positive and negative values represent opposite behavior on the same reviewed axis, and magnitude represents strength. If later evidence needs total intensity separately, add a separate intensity field rather than splitting every opposite pair by default.

Conceptual output:

```text
sector_context_state[available_time, sector_or_industry_symbol]
```

Planned physical output:

```text
trading_model.model_02_security_selection
```

The V1 field contract is owned by `src/models/model_02_security_selection/sector_context_state_contract.md` until implementation/evaluation proves which names should be shared through the registry.

Core state blocks:

```text
sector_observed_behavior_vector
sector_attribute_vector
sector_conditional_behavior_vector
sector_trend_stability_vector
sector_composition_vector
sector_tradability_vector
sector_risk_context_vector
eligibility_state
optional sector_selection_parameter
optional handoff_stock_universe_refs
```

Layer 2 may use ETF holdings and `stock_etf_exposure` for composition diagnostics and downstream handoff evidence. It must not choose final stocks, entry timing, strategy parameters, option contracts, final size, or portfolio weights.

## D007 - `stock_etf_exposure` is evidence, not the Layer 2 target

Date: 2026-05-02
Status: Accepted

ETF holdings are source-side evidence for eligible sector/industry equity ETFs. `stock_etf_exposure` is a source-backed aggregation used to explain basket composition, concentration, overlap, freshness, and possible downstream stock-universe references.

For Layer 2 V1, `stock_etf_exposure` is not a final stock-selection target and must not make Layer 2 behave as a hidden stock selector.

## D008 - Strategy fitting must use anonymous target candidates

Date: 2026-05-02
Status: Accepted

`StrategySelectionModel` and later target-aware layers may evaluate target candidates only through model-facing anonymous features.

Allowed in model-facing fitting vectors:

- target behavior shape;
- liquidity and tradability shape;
- sector context state;
- broad market context state;
- event/risk/cost context;
- strategy compatibility features.

Excluded from model-facing fitting vectors:

- raw ticker identity;
- company identity;
- memorized symbol-specific historical winner labels.

Real symbols may remain in audit/routing metadata and final decision records.

## D009 - OptionExpressionModel V1 is single-leg long options only

Date: 2026-04-28
Status: Accepted

`OptionExpressionModel` V1 supports only:

- stock/ETF direct expression as a comparison or fallback;
- long call;
- long put.

V1 must not choose debit spreads, calendars, diagonals, straddles, strangles, condors, butterflies, ratio spreads, or naked short options.

The model must use timestamped option-chain snapshots, bid/ask, liquidity, IV, Greeks, conservative fill assumptions, and market-context constraints such as DTE, delta/moneyness, IV/vega/theta tolerance, and no-trade filters.

## D010 - Model governance and promotion evidence stay model-local until accepted

Date: 2026-05-01
Status: Accepted

Model evaluation, config versions, promotion candidates, promotion decisions, rollback proposals, and active-pointer proposals are model-governance artifacts.

Current implementation provides dry-run/evidence-building paths first. Durable writes or production active-pointer changes require explicit accepted contracts and review.

The current table-name terms are registered in `trading-manager`; concrete column-level registration can wait until real evaluation/promotion flows prove the schema.
