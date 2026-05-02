# RFC: Seven-Layer Trading Model Architecture

Status: draft  
Date: 2026-04-27  
Owner intent: clarify model needs before changing data cleaning, feature tables, bundle composition, or implementation layout.

## Summary

The trading system should be designed as a point-in-time, regime-aware decision stack:

```text
data foundation
  ↓
1. MarketRegimeModel (`market_regime_model`)
  ↓
2. SecuritySelectionModel (`security_selection_model`)
  ↓
3. StrategySelectionModel (`strategy_selection_model`)
  ↓
4. TradeQualityModel (`trade_quality_model`)
  ↓
5. OptionExpressionModel (`option_expression_model`)
  ↓
6. EventOverlayModel (`event_overlay_model`)
  ↓
7. PortfolioRiskModel (`portfolio_risk_model`)
```

Layer 6 and Layer 7 are not simple downstream stages:

- **Layer 6 is an overlay** that can modify Layers 1-5 and the final risk gate.
- **Layer 7 is the final execution gate** and can reject, resize, delay, or alter any candidate trade.

The system should not answer only “buy or sell.” It should answer:

- What market state are we in?
- Which sector/industry baskets show the clearest rotation/trend evidence?
- Which strategy components should be combined into the final strategy for this candidate?
- Is this signal worth trading?
- What target, stop, holding time, and adverse/favorable excursion are expected?
- Given the broad market state, should the trade be expressed with stock, ETF, long call, or long put, and which contract constraints apply?
- Is there event risk or event opportunity?
- Does the current portfolio allow this trade?
- Given the broad market state, what size, execution style, and exit plan should be used?

## Canonical Layer Names

These names are canonical for docs, code, artifact metadata, and future registry proposals. Use the `stable id` in machine-facing paths/configs and the `model class` name in code/docs where PascalCase is appropriate.

Core separation rule:

```text
broad market background -> market-conditioned sector/industry trend-stability background -> anonymized strategy-aware target subject
```

Layer 1 describes the market environment. Layer 2 describes which sector/industry baskets have stable trends under each market environment. Final target/security selection is model-facing only as an anonymized candidate until downstream strategy, trade-quality, option-expression, event, and portfolio constraints are known.

| Layer | Model class | Stable id | Chinese name | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 | Describe point-in-time broad market state, market-property factors, confidence, transition risk, and dominant macro/risk drivers without sector/industry candidate conclusions. |
| 2 | `SecuritySelectionModel` | `security_selection_model` | 板块/行业选择模型 | Select tradable sector/industry baskets by studying which sectors have trend-stable behavior under each broad market state; ETF holdings/exposure are composition diagnostics, broad market state is conditioning context, and final stock selection waits for anonymized strategy-aware downstream layers. |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 | Compose and weight multiple strategy components for anonymized target candidates conditioned on target shape, broad market background, sector/industry trend-stability context, cost, and robustness; avoid ticker-identity learning. |
| 4 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 | Score candidate signals and predict trade outcome distribution, target/stop, MFE/MAE, and holding horizon. |
| 5 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 | Choose stock/ETF/long-call/long-put expression and option-contract constraints from signal forecast, option chain, liquidity, IV, Greeks, and broad market-state background. V1 excludes multi-leg option structures. |
| 6 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 | Overlay scheduled/breaking event risk, abnormal activity, and event-memory adjustments across earlier layers and the risk gate. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 | Final offline risk, sizing, exposure, execution-style, exit-rule, and kill-switch model using market-state background plus portfolio reality. |

Naming rule: do not call Layer 7 simply `ExecutionModel`, because live/paper order placement is outside `trading-model`. `PortfolioRiskModel` may describe execution-gate logic but does not mutate brokerage state.

## Revised Model Structure

The current accepted structure is:

```text
1. Market context
   model_01_market_regime
   -> market_context_state

2. Sector/industry context
   model_02_security_selection
   -> sector_market_condition_profile
   -> sector_trend_stability_vector
   -> sector_selection_parameter_surface

3. Anonymous target + strategy context
   target_candidate_builder / model_03_strategy_selection
   -> target_candidate_id
   -> anonymous_target_feature_vector
   -> strategy_fit_state / composite_strategy_recommendation

4+. Trade construction and approval
   trade_quality -> option_expression -> event_overlay -> portfolio_risk
```

Layer 2 is a market-state-conditioned sector trend-stability model. It is not a stock selector. Layer 3 is the first point where a target candidate is evaluated, and the model-facing row should be anonymous: ticker identity is retained for audit/routing outside the fitting vector, not used as a learned identity feature.

## Non-negotiable Point-in-Time Rule

Every model and feature must obey:

```text
At time t, the model may only use data genuinely available before or at t.
```

The data foundation must distinguish at least these times when applicable:

| Time | Meaning |
|---|---|
| `event_time` | When the underlying event occurred or became scheduled to occur. |
| `available_time` | When the data/evidence became visible to the system. |
| `tradeable_time` | Earliest time a strategy could realistically trade on it. |

Examples:

- Earnings release timestamp may be 16:05 ET.
- News/provider/system availability may be 16:07 ET.
- Earliest realistic trade may be 16:08 ET or next regular session, depending on asset/liquidity rules.

Backtests must use `available_time`/`tradeable_time`, not hindsight event interpretation.

## Repository Boundary Impact

The accepted `trading-model` scope is now the full seven-layer offline modeling architecture. Implementation should still stay phased, with `MarketRegimeModel` as the likely first slice.

Recommended ownership split:

| Area | Likely owner |
|---|---|
| Source acquisition, source-evidence bundles | `trading-data` |
| Shared fields, identifiers, contracts, registry | `trading-manager` |
| Offline model research and validation | `trading-model` |
| Scheduling/routing/lifecycle | `trading-manager` control plane / execution-side repos |
| Live execution, order placement, broker integration | execution/risk repository, not `trading-model` |

If a later decision splits one or more layers into separate component repositories, update `docs/00_scope.md`, this RFC, and `trading-manager` registry/contracts together.

## Layer 1: MarketRegimeModel

### Goal

Describe current market conditions as a continuous point-in-time state vector using market-only features.

The model should capture deeper market properties, not merely surface ETF-ratio proxies. The accepted conceptual ontology is:

- price behavior / 价格
- trend certainty / 趋势
- capital flow and funding/liquidity / 资金
- sentiment and risk appetite / 情绪
- valuation and discount-rate pressure / 估值
- fundamental strength and growth quality / 基本面
- macro and policy environment / 宏观
- market-wide structure, breadth, concentration, crowding, and correlation / 结构
- risk stress, tail pressure, and transition risk / 风险

V1 does **not** need discrete clustering, hard regime labels, HMM states, human-readable state names, ETF rankings, sector/industry rotation conclusions, sector leadership rankings, or security candidates. Those can be research diagnostics or downstream outputs later, but they are not the Layer 1 contract.

Sector/industry rotation is a Layer 2 problem. Layer 1 may describe aggregate tape structure, breadth, crowding, correlation, and fragility, but it should not answer which sector or industry is currently the best candidate.

### Input table

```text
trading_data.feature_01_market_regime
```

This table is the deterministic Layer 1 feature surface. It contains observable evidence such as returns, relative strength, volatility, trend/momentum, correlation, breadth, credit/rate proxies, dollar/commodity proxies, and other measurement signals. Those signals are sensors; the Model 1 output should be the deeper market-property state vector inferred from them.

### First model method

Start simple, point-in-time, and interpretable:

```text
rolling/expanding scaler
+ measurement/proxy standardization
+ evidence aggregation by market-property ontology
+ bounded continuous latent market-property vector
```

No supervised labels are assigned. No clustering is required for V1. Future-return labels may be used only for evaluation, never as inputs to construct the market-state vector.

### Conceptual output ontology

The durable Model 1 contract should move toward market-property fields such as:

```json
{
  "available_time": "2026-04-28T10:00:00-04:00",
  "price_behavior_factor": 0.44,
  "trend_certainty_factor": 0.63,
  "capital_flow_factor": 0.31,
  "sentiment_factor": 0.49,
  "valuation_pressure_factor": -0.12,
  "fundamental_strength_factor": 0.28,
  "macro_environment_factor": 0.09,
  "market_structure_factor": 0.41,
  "risk_stress_factor": 0.21,
  "transition_risk_factor": 0.22,
  "data_quality_score": 0.97
}
```

ETF ratios, spreads, relative strength pairs, and other observed signals remain valid input evidence, but they should not be mistaken for the final factor ontology. Cross-asset macro/risk proxies such as `HYG/LQD`, `TLT/SHY`, `IEF/SHY`, `UUP/SPY`, or `GLD/SPY` may remain Model 1 sensors when they infer broad credit/funding, discount-rate, dollar-liquidity, inflation/safe-haven, or risk-pressure states. Sector/industry ETF comparisons that answer candidate leadership or rotation belong to Model 2.

Current implementation columns now use this market-property ontology, but many remain proxy-backed slices; supporting evidence definitions should mature as richer point-in-time data becomes available.

### Evaluation

- point-in-time correctness and no leakage
- vector stability under rolling/expanding fits
- downstream usefulness for option expression, strategy compatibility, and portfolio risk/execution policy without leaking downstream selection labels into Layer 1
- interpretability of market-property factors and their supporting evidence signals
- drawdown warning usefulness

## Layer 2: SecuritySelectionModel

### Goal

Select the sector/industry baskets that are easiest and cleanest to trade now, with special attention to which broad-market environments make each sector trend-stable. Layer 2 V1 is a sector/industry selection model, not a final stock selector. Trend-stable means persistent directional behavior or clear cyclical regularity, not low price volatility.

It answers:

- Which sector/industry ETFs show the clearest, most persistent, least ambiguous leadership, and under which broad market states does that trend remain stable?
- Which sector/industry baskets have enough breadth, liquidity, optionability, composition quality, and event cleanliness to be worth downstream strategy work?
- Which baskets are eligible, watch-only, or gated out because they are noisy, stale, illiquid, event-dense, or compositionally fragile?

Individual stocks are the final objects of interest, but selecting them before `StrategySelectionModel` decides the compatible trading approach is premature. ETF holdings and `stock_etf_exposure` remain evidence and handoff context, not the Layer 2 V1 target.

This layer does not output final stocks, entry timing, strategy parameters, option contracts, final position size, or final portfolio weights.

### Inputs

- Feature 02 sector/industry rotation rows: sector-vs-broad, industry-vs-sector, sector-vs-sector, daily-context relative strength, trend, volatility, correlation, and breadth/dispersion evidence.
- ETF holdings snapshots: constituent weights for eligible sector/industry equity ETFs, used for basket composition and transmission diagnostics.
- `stock_etf_exposure`: source-backed exposure evidence used to explain basket composition and provide optional downstream stock-universe references, not to select final stocks in Layer 2 V1.
- ETF bars/liquidity: relative strength vs sector/broad benchmarks, trend clarity, trend persistence, volatility fit, gap behavior, volume expansion, spread/liquidity.
- ETF optionability summaries if the basket itself may be traded or used as an options proxy.
- Event exclusions: earnings concentration, known macro/event shock windows, SEC/news risk, abnormal activity flags.
- `MarketRegimeModel` outputs only as background/reference or coarse gating context, not as a direct sector/stock ranking transform.

### Sector/industry parameters

`SecuritySelectionModel` should build a sector/industry parameter surface from rotation evidence and tradability/composition/risk fields. It should not define a Layer-1-to-Layer-2 bridge such as `market_parameterizer(model_01_market_regime_vector)` or `sector_weighted_market_context_vector` for stock ranking.

Core conceptual fields:

```text
sector_rotation_state_vector
sector_market_condition_profile
sector_trend_stability_vector
sector_trend_clarity_score
sector_certainty_score
sector_composition_vector
sector_tradability_vector
sector_selection_parameter   # optional/convenience scalar, not sole context
```

Interpretation:

- `sector_rotation_state_vector` describes a sector/industry ETF's leadership, relative-strength persistence, breadth, trend stability, and signal agreement.
- `sector_market_condition_profile` describes which broad market states make that sector's trend easier or harder to trade.
- `sector_trend_stability_vector` describes directional persistence, monotonicity, pullback regularity, breakdown persistence, cycle regularity, false-break frequency, and choppiness.
- `sector_composition_vector` describes what the basket actually contains: holdings concentration, top-name dominance, freshness, coverage, and exposure diagnostics.
- `sector_tradability_vector` describes whether the basket is practical to trade or route into later strategy work.
- `sector_selection_parameter`, if produced, is a convenience scalar for sorting. It must be persisted with enough supporting context that downstream consumers can inspect why the basket was strong.

Sketch:

```text
sector_rotation_state_vector[sector_etf] = rotation_model(feature_02_security_selection_rows)

sector_composition_vector[sector_etf] = holdings_composition_model(source_02_security_selection, stock_etf_exposure)

sector_selection_parameter_surface = parameter_adjuster(
  sector_rotation_state_vector,
  sector_market_condition_profile,
  sector_trend_stability_vector,
  sector_trend_clarity_score,
  sector_certainty_score,
  sector_composition_vector,
  sector_tradability_vector,
  sector_event_risk_vector
)

sector_selection_parameter = optional_scalar_projection(sector_selection_parameter_surface)
```

Top-N sector selection is an operational usage of those parameters, and scalar projection must not be the only retained context.

### ETF holdings exposure matrix

`SecuritySelectionModel` should use sector/industry ETF holdings to understand what each basket represents and to prepare optional handoff references for later layers.

A useful derived representation remains:

```text
rows: stocks
columns: eligible sector/industry ETFs
values: holding weight
```

Example:

```json
{
  "symbol": "NVDA",
  "etf_membership": ["XLK", "SMH", "SOXX", "IGV"],
  "holding_weights": {
    "XLK": 0.12,
    "SMH": 0.20,
    "SOXX": 0.09
  }
}
```

In V1 this representation supports composition diagnostics and downstream handoff. It should not cause Model 2 to emit NVDA as the selected target before strategy selection.

### Tradable ETF universe

V1 parameter rows are limited to eligible sector/industry equity ETFs. The tradable ETF universe excludes broad index/style ETFs such as `SPY`, `QQQ`, `IWM`, `DIA`, and `RSP`, and non-equity macro/cross-asset ETFs such as `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `DBC`, `USO`, `UUP`, `VIXY`, `HYG`, and `LQD`.

Excluded ETFs can still be useful as MarketRegimeModel state inputs, risk filters, benchmark relatives, or portfolio-risk references. They are not emitted as Model 2 tradable parameter rows in V1.

### Parameter objective

`SecuritySelectionModel` does **not** output the sector/industry ETF or stock with the highest realized or expected return. It adjusts `sector_selection_parameter` higher when the sector/industry basket has:

```text
clear, persistent sector/industry leadership
high certainty / low ambiguity
strong relative strength with broad participation
enough liquidity and optionability
acceptable event and volatility risk
healthy composition and fresh holdings evidence
```

Forward returns are labels for evaluation and calibration, not direct production inputs. Ranking by `sector_selection_parameter` is allowed as a downstream usage pattern, but the model output remains a sector/industry parameter surface.

### Output sketch

```json
{
  "available_time": "2026-04-28T09:30:00-04:00",
  "sector_parameter_rows": [
    {
      "sector_or_industry_symbol": "SMH",
      "basket_type": "industry_etf",
      "sector_selection_parameter": 0.89,
      "sector_rotation_state_vector": {"relative_strength_score": 0.88, "leadership_persistence_score": 0.84, "breadth_support_score": 0.77},
      "sector_composition_vector": {"top_holding_concentration_score": 0.42, "holdings_freshness_score": 0.95},
      "trend_clarity_score": 0.92,
      "trend_persistence_score": 0.87,
      "certainty_score": 0.84,
      "eligibility_state": "eligible",
      "handoff_stock_universe_refs": ["stock_etf_exposure:SMH:2026-04-28"],
      "selection_reason": ["clear semiconductor leadership", "persistent relative strength", "acceptable volatility", "fresh holdings evidence"]
    }
  ],
  "gated_rows": [
    {"sector_or_industry_symbol": "ABC", "eligibility_state": "gated", "reason": "holdings stale"},
    {"sector_or_industry_symbol": "DEF", "eligibility_state": "gated", "reason": "liquidity too weak"}
  ]
}
```

### Data organization implication

This layer creates a direct need for two source-backed data products, scoped to eligible sector/industry equity ETFs first:

- `etf_holding_snapshot` / `source_02_security_selection` — issuer-published constituent holdings, cleaned into the Layer 2 source surface.
- `stock_etf_exposure` — derived point-in-time stock-to-ETF exposure table used for composition diagnostics and downstream handoff, not Layer 2 final stock selection.

## Layer 3: StrategySelectionModel

### Goal

Compose the final strategy recommendation for an anonymized target candidate from multiple strategy components/families. The output should not be a single historical champion strategy; it should be a controlled blend or ordered set of components conditioned on anonymous target features, market background, sector/industry background, costs, and robustness. The model should not learn that a particular ticker is special; it should learn which anonymous target shapes are easiest to trade under the current market and sector states.

Target candidate handling:

- use an ephemeral `target_candidate_id`, not ticker identity, as the model-facing row id;
- include anonymized target features such as trend shape, relative-strength shape, liquidity/optionability, event state, and exposure/context features;
- include `market_context_state` and `sector_context_state` as inputs;
- exclude raw ticker, company name, permanent identity, and historical per-ticker champion labels from unsupervised strategy fitting;
- map the selected anonymous candidate back to the real symbol only after scoring/audit.

Candidate families/components:

- trend following
- breakout/breakdown
- pullback in trend
- mean reversion
- volatility contraction/expansion
- relative strength
- reversal after capitulation
- gap continuation/fade
- event-driven technical setup

### Variant design

Keep variants limited at first. Example parameters:

- lookback: 5, 10, 20, 40
- entry threshold: 1σ, 1.5σ, 2σ
- stop: 1ATR, 2ATR, 3ATR
- take profit: 1R, 2R, 3R
- max holding period: 3D, 5D, 10D, 20D
- trend/volume filters on/off

### Scoring principle

Do not select historical champions. Score components and the composite strategy while penalizing overfitting and instability:

```text
component_or_composite_score =
  OOS_expectancy
  + risk_adjusted_return
  - drawdown_penalty
  - tail_loss_penalty
  - turnover_cost_penalty
  - slippage_penalty
  - parameter_instability_penalty
  - small_sample_penalty
```

Required validation methods should include walk-forward validation, parameter-neighborhood stability, cost sensitivity, and later PBO/CSCV or Deflated Sharpe Ratio where practical.

## Layer 4: TradeQualityModel

### Goal

Meta-label and score candidate signals from Layer 2.

It should predict the distribution of a trade outcome, not only direction.

Labels may include:

- future N-day return
- target-first vs stop-first
- time to target
- time to stop
- MFE / MAE
- realized holding period
- win/loss/scratch
- return quantile

Triple-barrier labeling is the natural first framework:

```text
upper target barrier
lower stop barrier
max holding-time barrier
```

### First methods

Tree-based models are a good first slice because they are practical and interpretable:

- logistic/gradient boosting classifier for trade/no-trade
- regression or quantile regression for expected return distribution
- survival model later for holding period/time-to-target
- calibration model for probability quality

### Evaluation

- AUC / PR-AUC for quality separation
- Brier score and calibration curve
- expectancy by score decile
- drawdown reduction after filtering
- retained trade frequency
- target/stop accuracy
- holding-period error

## Layer 5: OptionExpressionModel

### Goal

Choose the best simple trading expression after `TradeQualityModel` produces expected underlying move, target, stop, and holding horizon.

V1 allowed option structures are single-leg only:

- long call
- long put

Stock/ETF direct expression may be compared as a fallback, but V1 option expression must not use multi-leg spreads.

Explicitly deferred until risk/margin, multi-leg execution, slippage, and exit realism are mature:

- call debit spread
- put debit spread
- calendar/diagonal
- straddle/strangle
- ratio spreads
- iron condor/butterfly
- naked short options

### Hard filters

- DTE range
- bid/ask spread threshold
- open interest minimum
- volume minimum
- delta range
- IV/IV percentile bounds
- max loss constraint
- event-risk constraint

### Market-state usage

Market state should enter this layer most directly. It can adjust contract-expression choices without becoming a stock selector:

- higher transition/risk stress can require longer DTE, higher liquidity, wider time buffers, or no-trade;
- high volatility/IV stress can tighten IV percentile, vega, and theta-decay constraints;
- strong low-fragility trend conditions can allow more directional long-call/long-put expressions;
- rate, credit, dollar, commodity, and risk-appetite context can change acceptable moneyness/delta and expected holding horizon.

### Scoring principle

Choose expected utility, not theoretical max return:

```text
option_score =
  expected_option_pnl
  * probability_of_profit
  - max_loss_penalty
  - theta_decay_penalty
  - spread_penalty
  - IV_crush_penalty
  - liquidity_penalty
  - event_risk_penalty
```

Backtests must use real option-chain snapshots, bid/ask, conservative fill logic, slippage assumptions, and failure-to-fill handling.

## Layer 6: EventOverlayModel

### Goal

Identify and quantify scheduled and breaking events that affect market state, strategy validity, signal quality, option expression, and risk limits.

Event submodels:

| Submodel | Purpose |
|---|---|
| Scheduled Event Model | CPI/FOMC/NFP/earnings and other known-time event risk. |
| Breaking News Shock Model | sudden news classification, direction, scope, and urgency. |
| Pre-event Abnormal Activity Model | price/volume/options/IV/skew anomalies before formal event evidence. |
| Event Impact Memory Model | historical analogs and impact distributions by event type/context. |

### Overlay effects

Layer 6 can:

- raise Layer 1 transition risk
- alter Layer 2 candidate selection or exclusions
- disable Layer 3 strategy families
- reduce Layer 4 signal quality
- alter Layer 5 DTE/structure/vega constraints
- force Layer 7 size reduction, no-trade, or kill-switch behavior

### Information-leakage risk

Never train pre-event models using post-event explanations. Every event row must preserve observable timing and source priority.

## Layer 7: PortfolioRiskModel

### Goal

Decide whether a candidate trade may be placed, at what size, through what execution style, and under what exit plan. This is the other primary consumer of broad market-state background: the market state should influence risk budget, order aggressiveness, slippage tolerance, holding permission, and kill-switch posture.

Inputs include:

- Layer 1 broad market-state vector, confidence, transition/risk stress, and dominant background drivers
- Layer 2 selected sector/industry basket and rotation/tradability context
- Layer 3 strategy recommendation and any strategy-aware security/target refinement
- Layer 4 signal quality
- Layer 5 option structure/liquidity
- Layer 6 event risk/opportunity
- current positions, cash, margin
- delta/gamma/theta/vega exposure
- sector/security/event correlation
- daily/weekly PnL and drawdown state
- liquidity/execution conditions

Hard limits should include:

- single-trade max loss
- daily/weekly loss limits
- strategy drawdown limits
- symbol/sector/event exposure limits
- aggregate Greek limits
- liquidity and spread limits
- correlation/concentration limits
- kill switch conditions

## Unified Decision Record

Every candidate trade should produce a complete point-in-time decision record for audit, attribution, replay, and retraining.

```json
{
  "timestamp": "2026-04-28T09:30:00-04:00",
  "symbol": "SMH",
  "direction": "long",
  "layer_1_regime": {
    "state_name": "high_vol_risk_off",
    "confidence": 0.67,
    "transition_risk": 0.42
  },
  "layer_2_security_selection": {
    "sector_or_industry_symbol": "SMH",
    "sector_selection_parameter": 0.91,
    "sector_rotation_state_vector": {"relative_strength_score": 0.88, "leadership_persistence_score": 0.84, "breadth_support_score": 0.77},
    "sector_composition_vector": {"top_holding_concentration_score": 0.42, "holdings_freshness_score": 0.95},
    "trend_clarity_score": 0.90,
    "certainty_score": 0.84,
    "selection_reason": ["clear semiconductor leadership", "persistent relative strength", "high option liquidity"]
  },
  "layer_3_strategy": {
    "composite_strategy_id": "trend_breakout_pullback_v1",
    "components": [
      {"family": "trend_following", "weight": 0.55, "variant_id": "TF_20_2ATR_10D"},
      {"family": "breakout", "weight": 0.30, "variant_id": "BO_12_3ATR_5D"},
      {"family": "pullback_in_trend", "weight": 0.15, "variant_id": "PB_10_2ATR_5D"}
    ],
    "composite_strategy_score": 0.74
  },
  "layer_4_signal_quality": {
    "trade_quality_score": 0.72,
    "probability_of_profit": 0.58,
    "expected_return": 0.024,
    "target_price": 255.0,
    "stop_price": 238.0,
    "expected_holding_days": 4
  },
  "layer_5_option_expression": {
    "structure": "long_call",
    "contracts": ["SMH 2026-05-15 250C"],
    "market_state_contract_adjustment": {"dte_bias": "longer", "delta_band": "0.55-0.70", "iv_tolerance": "normal"},
    "expected_option_pnl": 1.35,
    "max_loss": 3.2,
    "liquidity_score": 0.88,
    "option_score": 0.76
  },
  "layer_6_event_overlay": {
    "event_risk_score": 0.38,
    "event_type": "none_major",
    "action": "normal"
  },
  "layer_7_portfolio_risk": {
    "decision": "approved",
    "size": 5,
    "market_state_execution_policy": {"risk_budget": "normal", "order_aggressiveness": "passive_limit", "overnight_allowed": true},
    "order_type": "limit",
    "limit_price": 3.2,
    "max_slippage": 0.08,
    "exit_plan": {
      "profit_take": "+60%",
      "stop_loss": "-35%",
      "time_stop": "5D"
    }
  }
}
```

This record is the spine for:

- backtest replay
- trade logs
- risk audit
- model attribution
- live monitoring
- model retraining

## Validation Framework

Use time-series walk-forward validation, not random train/test splits.

Example rolling framework:

```text
2015-2019 train → 2020 validation → 2021 test
2016-2020 train → 2021 validation → 2022 test
...
```

Rules:

- model selection only in train/validation windows
- test window is evaluation-only
- no layer can use future data
- option chains must be timestamped snapshots
- event data must use `available_time` and `tradeable_time`
- slippage, fees, and failed fills must be modeled

## Phased Implementation Recommendation

Do not build all seven layers at once.

### Phase 1: Data foundation + Layer 1

Deliver:

- market-state feature dataset contract
- rolling/expanding regime model prototype
- market-state vector and transition-risk outputs
- market-state dashboard/data artifact sketch
- per-state market behavior statistics
- first evidence that states are stable, interpretable, and useful for option expression and risk/execution policy

### Phase 2: Layer 2 security selection

Deliver:

- Sector/industry ETF holdings exposure matrix
- `stock_etf_exposure` derived table proposal for composition diagnostics and downstream handoff
- full-market scan candidate logic
- long/short/watch/excluded candidate pools
- optionability and liquidity filters
- sector/industry rotation transmission evidence from ETF rotation context to stocks

### Phase 3: Layer 3 strategy library

Deliver:

- small strategy-family library
- limited variants
- candidate/market-background-conditioned performance table
- disabled strategy list
- parameter-neighborhood stability evidence

### Phase 4: Layer 4 signal quality model

Deliver:

- underlying-only trade labels
- triple-barrier labeling implementation
- trade quality score
- expected return / target / stop / holding-time outputs
- score-decile performance evidence

### Phase 5: Layer 5 option selector

Deliver:

- option-chain snapshot feature contract
- long call/put ranker only
- market-state-conditioned DTE/delta/moneyness/IV constraints
- liquidity/IV/crush filters
- expected option PnL and fill/slippage assumptions

### Phase 6: Layer 6 event overlay

Deliver:

- scheduled event risk score
- earnings IV-crush model
- macro event risk model
- abnormal option/price/volume activity detector
- stock/equity abnormal activity detector
- overlay adjustment rules for Layers 1-5 and Layer 7

### Phase 7: Layer 7 risk/execution gate

Deliver:

- position sizing engine
- exposure monitor
- market-state-conditioned order/execution rules
- exit lifecycle rules
- kill switch
- PnL and attribution dashboard contract

## Immediate Next Design Questions

Before implementation, decide:

1. What exact sector/industry ETF basket should `SecuritySelectionModel` use first?
2. What first sector/industry rotation state vector should Model 2 output, and which Feature 02 evidence families define trend clarity, persistence, breadth, and certainty?
3. What is the first tradable universe for Phase 2? Sector/industry ETF basket only, liquid mega-cap equities, or both?
4. What timestamp fields should be globally registered for model-facing event/evidence rows: `event_time`, `available_time`, `tradeable_time`, and ET/UTC variants?
5. What is the first label horizon for underlying trades: intraday, 1D, 5D, 10D, or multi-horizon?
6. How exactly should `MarketRegimeModel` state adjust `OptionExpressionModel` contract constraints such as DTE, delta/moneyness, IV tolerance, and no-trade filters?
7. How exactly should `MarketRegimeModel` state adjust `PortfolioRiskModel` execution/risk policy such as risk budget, order aggressiveness, slippage tolerance, overnight permission, and kill-switch posture?
8. Should `stock_etf_exposure` be registered as a derived data kind in `trading-manager`, or remain model-local until SecuritySelectionModel proves useful?
9. Should Phase 1 produce only offline research artifacts, or also a ready-signal contract for later execution systems?
