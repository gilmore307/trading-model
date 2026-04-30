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
- Which strategy family is appropriate in this state?
- Is this signal worth trading?
- What target, stop, holding time, and adverse/favorable excursion are expected?
- Should the trade be expressed with stock, ETF, long call, or long put?
- Is there event risk or event opportunity?
- Does the current portfolio allow this trade?
- What size, execution style, and exit plan should be used?

## Canonical Layer Names

These names are canonical for docs, code, artifact metadata, and future registry proposals. Use the `stable id` in machine-facing paths/configs and the `model class` name in code/docs where PascalCase is appropriate.

| Layer | Model class | Stable id | Chinese name | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 | Describe point-in-time broad market state, market-property factors, confidence, transition risk, and dominant macro/risk drivers without sector/industry candidate conclusions. |
| 2 | `SecuritySelectionModel` | `security_selection_model` | 标的选择模型 | Build candidate tradable universes from regime/sector style, sector/industry ETF holdings exposure, stock relative strength, liquidity, optionability, and event exclusions. |
| 3 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 | Select strategy family/variant conditioned on regime, candidate symbol, cost, and robustness evidence. |
| 4 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 | Score candidate signals and predict trade outcome distribution, target/stop, MFE/MAE, and holding horizon. |
| 5 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 | Choose stock/ETF/long-call/long-put expression from signal forecast, option chain, liquidity, IV, and Greeks. V1 excludes multi-leg option structures. |
| 6 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 | Overlay scheduled/breaking event risk, abnormal activity, and event-memory adjustments across earlier layers and the risk gate. |
| 7 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 | Final offline risk, sizing, exposure, execution-gate, exit-rule, and kill-switch model. |

Naming rule: do not call Layer 7 simply `ExecutionModel`, because live/paper order placement is outside `trading-model`. `PortfolioRiskModel` may describe execution-gate logic but does not mutate brokerage state.

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

Current implementation columns such as `trend_factor`, `credit_stress_factor`, and `risk_appetite_factor` are the first proxy-backed slice and should be migrated toward this deeper ontology as Model 1 matures.

### Evaluation

- point-in-time correctness and no leakage
- vector stability under rolling/expanding fits
- downstream usefulness for security selection and strategy selection without leaking downstream selection labels into Layer 1
- interpretability of market-property factors and their supporting evidence signals
- drawdown warning usefulness

## Layer 2: SecuritySelectionModel

### Goal

Study sector/industry rotation and build candidate-level selection parameters for the current tradable sector/industry ETF and stock universe after `MarketRegimeModel` identifies broad market conditions.

It answers:

- What is the adjusted `candidate_selection_parameter` for each eligible sector/industry ETF or stock?
- Which candidates are eligible, watch-only, or gated out because of liquidity, event risk, poor optionability, or unstable trend state?
- Which sector/industry ETF market parameter should be transmitted into stock-level candidate vectors through ETF holdings exposure?

This layer does not output "the selected ETF", entry timing, strategy parameters, option contracts, final position size, or final portfolio weights. Sorting by `candidate_selection_parameter` and choosing the highest-parameter ETF is a downstream usage pattern, not the durable Model 2 output contract.

### Inputs

- `MarketRegimeModel` outputs: continuous broad market-state vector, risk-on/risk-off context, transition pressure, and dominant macro/risk drivers. It does not output sector/style condition factors, sector rankings, ETF rankings, or selected securities.
- Model 2 market parameters derived from the Layer 1 vector: base tape trend certainty, transition/turning risk, and sector-weighted market parameters.
- ETF holdings snapshots: constituent weights for eligible sector/industry equity ETFs. Broad index ETFs and non-equity macro ETFs may remain state inputs or filters, but they are not V1 tradable ETF candidates.
- ETF and stock bars/liquidity: relative strength vs sector ETF and SPY, trend clarity, trend persistence, volatility fit, gap behavior, volume expansion, spread/liquidity.
- Optionability summaries: option availability, spread, volume, open interest, DTE coverage.
- Event exclusions: earnings proximity, known macro/event shock windows, SEC/news risk, abnormal activity flags.

### Market and selection parameters

`SecuritySelectionModel` should not feed the full Layer 1 vector directly into every candidate parameter without interpretation. It also should not encode candidate choice as a hand-written additive formula. Instead, it owns a parameter adjustment step: convert the market-state vector into market parameters, attach the appropriate market parameter to each candidate vector, and adjust that candidate's final selection parameter.

Core conceptual parameters:

```text
market_trend_certainty_parameter
market_transition_risk_parameter
base_market_parameter
sector_weighted_market_parameter
candidate_market_parameter
candidate_selection_parameter
```

Interpretation:

- `market_trend_certainty_parameter` captures whether the overall tape has a clear, coherent trend backdrop.
- `market_transition_risk_parameter` captures broad-market turning/phase-change risk.
- `base_market_parameter` is the unweighted market parameter used when a candidate has no reliable sector/industry ETF mapping.
- `sector_weighted_market_parameter` is a sector/industry-specific version of the market parameter, produced by applying a sector factor-weight vector to the Layer 1 state vector.
- `candidate_market_parameter` is the market parameter inserted into a specific ETF or stock candidate vector. For a sector/industry ETF it equals that ETF's sector-weighted value; for a stock with ETF exposure it is the exposure-weighted blend of its mapped sector/industry ETF values; for an unmapped stock it falls back to `base_market_parameter`.
- `candidate_selection_parameter` is the final Model 2 parameter for that candidate. It is the output to persist; selecting the highest value is a consumer action.

Sketch:

```text
base_market_parameter = market_parameterizer(model_01_market_regime_vector)

sector_weighted_market_parameter[sector_etf] =
  market_parameterizer(model_01_market_regime_vector, sector_etf_factor_weight_vector)

candidate_market_parameter =
  sector_weighted_market_parameter[candidate_symbol]                         # sector/industry ETF
  or exposure_weighted_blend(sector_weighted_market_parameter, stock_etf_exposure)
  or base_market_parameter                                                   # unmapped stock fallback

candidate_selection_parameter = parameter_adjuster(
  candidate_market_parameter,
  candidate_trend_state_vector,
  candidate_certainty_state_vector,
  tradability_and_risk_vector
)
```

`parameter_adjuster` may start as a transparent calibrated rule, monotonic transform, or small learned model, but the contract should remain parameter-centric. The model's responsibility is to produce stable candidate-level parameters; top-N selection is an operational usage of those parameters.

### ETF holdings exposure matrix

`SecuritySelectionModel` should use sector/industry ETF holdings as the bridge from sector/industry rotation evidence to individual tradable symbols.

A core derived representation is:

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

Then sector/industry ETF market parameters can be transmitted to stocks:

```text
stock_candidate_market_parameter = exposure_weighted_blend(sector_weighted_market_parameter, stock_etf_exposure)
```

### Tradable ETF universe

V1 ETF parameter rows are limited to sector/industry equity ETFs whose holdings can transmit into stock candidates. The tradable ETF universe excludes broad index/style ETFs such as `SPY`, `QQQ`, `IWM`, `DIA`, and `RSP`, and non-equity macro/cross-asset ETFs such as `TLT`, `IEF`, `SHY`, `GLD`, `SLV`, `DBC`, `USO`, `UUP`, `VIXY`, `HYG`, and `LQD`.

Excluded ETFs can still be useful as MarketRegimeModel state inputs, risk filters, benchmark relatives, or portfolio-risk references. They are not emitted as Model 2 tradable ETF parameter rows in V1.

### Parameter objective

`SecuritySelectionModel` does **not** output the sector/industry ETF or stock with the highest realized or expected return. It adjusts `candidate_selection_parameter` higher when the candidate has:

```text
clear, persistent trend
high certainty / low ambiguity
enough liquidity and optionability
acceptable event and volatility risk
a market parameter that supports this candidate's sector/industry state
```

Forward returns are labels for evaluation and calibration, not direct production inputs. Ranking by `candidate_selection_parameter` is allowed as a downstream usage pattern, but the model output remains a candidate-parameter surface.

### Candidate sources

Do not rely only on ETF holdings. Build parameter rows from two candidate sources:

1. **Sector/industry ETF holdings-driven universe** — captures core holdings, style exposure, ETF overlap, and crowded/funded themes.
2. **Full-market scan-driven universe** — captures emerging opportunities that are not yet core ETF weights.

### Parameter adjustment sketch

```text
candidate_selection_parameter = parameter_adjuster(
  candidate_market_parameter,
  trend_clarity_score,
  trend_persistence_score,
  relative_strength_consistency_score,
  signal_agreement_score,
  liquidity_score,
  optionability_score,
  choppiness_state,
  volatility_instability_state,
  event_risk_state
)
```

The sketch deliberately avoids fixed `+ w` / `- w` arithmetic. Additive coefficients may be one implementation candidate, but they are not the model contract.

### Output sketch

```json
{
  "available_time": "2026-04-28T09:30:00-04:00",
  "parameter_rows": [
    {
      "candidate_symbol": "SMH",
      "candidate_type": "industry_etf",
      "candidate_selection_parameter": 0.89,
      "candidate_market_parameter": 0.78,
      "market_transition_risk_parameter": 0.16,
      "trend_clarity_score": 0.92,
      "trend_persistence_score": 0.87,
      "certainty_score": 0.84,
      "eligibility_state": "eligible",
      "candidate_reason": ["clear semiconductor leadership", "persistent relative strength", "acceptable volatility"]
    },
    {
      "candidate_symbol": "NVDA",
      "candidate_type": "stock",
      "candidate_selection_parameter": 0.91,
      "candidate_market_parameter": 0.76,
      "etf_holding_exposure": {"SMH": 0.20, "XLK": 0.12, "SOXX": 0.09},
      "relative_strength_score": 0.88,
      "trend_clarity_score": 0.91,
      "trend_persistence_score": 0.86,
      "certainty_score": 0.84,
      "optionability_score": 0.95,
      "event_risk_score": 0.32,
      "eligibility_state": "eligible",
      "candidate_reason": ["core holding of strong semiconductor ETFs", "persistent relative strength vs SMH and XLK", "clear trend with high option liquidity"]
    }
  ],
  "gated_rows": [
    {"candidate_symbol": "ABC", "eligibility_state": "gated", "reason": "earnings within 24 hours"},
    {"candidate_symbol": "DEF", "eligibility_state": "gated", "reason": "option spread too wide"}
  ]
}
```

### Data organization implication

This layer creates a direct need for two data products, scoped to eligible sector/industry equity ETFs first:

- `etf_holding_snapshot` — issuer-published constituent holdings, already scaffolded in `trading-data`.
- `stock_etf_exposure` — derived point-in-time stock-to-ETF exposure table for sector/theme/style transmission.

## Layer 3: StrategySelectionModel

### Goal

Choose strategy family and variant for a symbol under the current regime.

Candidate families:

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

Do not select historical champions. Penalize overfitting and instability:

```text
variant_score =
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

Decide whether a candidate trade may be placed, at what size, through what execution style, and under what exit plan.

Inputs include:

- Layer 1 regime/confidence
- Layer 2 selected symbol/candidate pool context
- Layer 3 strategy recommendation
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
    "candidate_selection_parameter": 0.91,
    "candidate_market_parameter": 0.76,
    "market_transition_risk_parameter": 0.16,
    "trend_clarity_score": 0.90,
    "certainty_score": 0.84,
    "candidate_reason": ["core holding of strong semiconductor ETFs", "clear persistent trend", "high option liquidity"]
  },
  "layer_3_strategy": {
    "family": "breakdown_trend_following",
    "variant_id": "BT_12_3ATR_5D",
    "strategy_score": 0.74
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
- regime probability and transition-risk outputs
- regime dashboard/data artifact sketch
- per-regime market behavior statistics
- first evidence that regimes are stable, interpretable, and useful

### Phase 2: Layer 2 security selection

Deliver:

- Sector/industry ETF holdings exposure matrix
- `stock_etf_exposure` derived table proposal
- full-market scan candidate logic
- long/short/watch/excluded candidate pools
- optionability and liquidity filters
- sector/industry rotation transmission evidence from ETF candidate parameters to stocks

### Phase 3: Layer 3 strategy library

Deliver:

- small strategy-family library
- limited variants
- regime/security-conditioned performance table
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
- order/execution rules
- exit lifecycle rules
- kill switch
- PnL and attribution dashboard contract

## Immediate Next Design Questions

Before implementation, decide:

1. What exact sector/industry ETF basket and base equity universe should `SecuritySelectionModel` use first?
2. What initial sector factor-weight matrix should convert the Layer 1 vector into `sector_weighted_market_parameter`?
3. What is the first tradable universe for Phase 2? Sector/industry ETF basket only, liquid mega-cap equities, or both?
4. What timestamp fields should be globally registered for model-facing event/evidence rows: `event_time`, `available_time`, `tradeable_time`, and ET/UTC variants?
5. What is the first label horizon for underlying trades: intraday, 1D, 5D, 10D, or multi-horizon?
6. Should `stock_etf_exposure` be registered as a derived data kind in `trading-manager`, or remain model-local until SecuritySelectionModel proves useful?
6. Should Phase 1 produce only offline research artifacts, or also a ready-signal contract for later execution systems?
