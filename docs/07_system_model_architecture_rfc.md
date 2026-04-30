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
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 | Detect point-in-time market regime, sector/style conditions, state probabilities, confidence, transition risk, and dominant drivers. |
| 2 | `SecuritySelectionModel` | `security_selection_model` | 标的选择模型 | Build candidate tradable universes from regime/sector style, ETF holdings exposure, stock relative strength, liquidity, optionability, and event exclusions. |
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

The model should capture usable downstream context for:

- risk appetite
- volatility stress
- rate pressure
- dollar pressure
- commodity pressure
- sector rotation
- market breadth
- cross-asset correlation stress
- trend strength
- transition pressure

V1 does **not** need discrete clustering, hard regime labels, HMM states, or human-readable state names. Those can be research diagnostics later, but they are not the main contract for selecting securities or strategies.

### Input table

```text
trading_data.feature_01_market_regime
```

This table is the deterministic Layer 1 feature surface. It contains the reviewed V1 feature families: returns, relative strength, volatility, trend/momentum, and correlation/breadth.

### First model method

Start simple, point-in-time, and interpretable:

```text
rolling/expanding scaler
+ feature-block standardization
+ block-level factor/score extraction
+ bounded continuous market-state vector
```

No supervised labels are assigned. No clustering is required for V1. Future-return labels may be used only for evaluation, never as inputs to construct the market-state vector.

### Output contract sketch

```json
{
  "available_time": "2026-04-28T10:00:00-04:00",
  "trend_factor": 0.63,
  "volatility_stress_factor": 0.21,
  "correlation_stress_factor": 0.34,
  "credit_stress_factor": 0.18,
  "rate_pressure_factor": -0.12,
  "dollar_pressure_factor": 0.09,
  "commodity_pressure_factor": 0.27,
  "sector_rotation_factor": 0.41,
  "breadth_factor": 0.58,
  "risk_appetite_factor": 0.49,
  "transition_pressure": 0.22,
  "data_quality_score": 0.97
}
```

### Evaluation

- point-in-time correctness and no leakage
- vector stability under rolling/expanding fits
- downstream usefulness for security selection and strategy selection
- interpretability of feature-block factors
- drawdown warning usefulness

## Layer 2: SecuritySelectionModel

### Goal

Construct the current tradable symbol universe after `MarketRegimeModel` identifies market, sector, and style conditions.

It answers:

- Which stocks or ETFs deserve attention now?
- Which symbols are long candidates, short candidates, watch-only, or excluded?
- Should the system trade sector ETFs directly, core ETF holdings, high-relative-strength leaders, laggards/rotation candidates, defensive stocks, or only very liquid mega-caps?
- Which candidates are excluded because of liquidity, event risk, or poor optionability?

This layer does not choose entry timing, strategy parameters, option contracts, or final position size.

### Inputs

- `MarketRegimeModel` outputs: market regime, sector/style regime, risk-on/risk-off score, transition risk, dominant macro drivers, sector ETF scores.
- ETF holdings snapshots: ETF constituent weights for broad, sector, industry, and thematic ETFs.
- Stock bars/liquidity: relative strength vs sector ETF and SPY, trend quality, volatility, gap behavior, volume expansion, spread/liquidity.
- Optionability summaries: option availability, spread, volume, open interest, DTE coverage.
- Event exclusions: earnings proximity, known macro/event shock windows, SEC/news risk, abnormal activity flags.

### ETF holdings exposure matrix

`SecuritySelectionModel` should use ETF holdings as the bridge from sector/style regime to individual tradable symbols.

A core derived representation is:

```text
rows: stocks
columns: ETFs
values: holding weight
```

Example:

```json
{
  "symbol": "NVDA",
  "etf_membership": ["QQQ", "XLK", "SMH", "SOXX", "AIQ"],
  "holding_weights": {
    "QQQ": 0.08,
    "XLK": 0.12,
    "SMH": 0.20
  }
}
```

Then sector/style scores from `MarketRegimeModel` can be transmitted to stocks:

```text
stock_sector_exposure_score = sum(etf_score * stock_weight_in_etf)
```

### Candidate sources

Do not rely only on ETF holdings. Use two candidate sources:

1. **ETF holdings-driven universe** — captures core holdings, style exposure, ETF overlap, and crowded/funded themes.
2. **Full-market scan-driven universe** — captures emerging opportunities that are not yet core ETF weights.

### Scoring sketch

```text
target_score =
  w1 * sector_regime_fit
+ w2 * etf_holding_exposure
+ w3 * stock_relative_strength
+ w4 * stock_trend_quality
+ w5 * liquidity_score
+ w6 * optionability_score
+ w7 * historical_strategy_fit
- w8 * event_risk_penalty
- w9 * crowding_penalty
- w10 * volatility_penalty
```

### Output sketch

```json
{
  "timestamp": "2026-04-28T09:30:00-04:00",
  "market_regime": "low_vol_risk_on",
  "preferred_sector_etfs": ["SMH", "XLK", "IGV", "QQQ"],
  "avoid_sector_etfs": ["XLU", "XLRE"],
  "long_candidates": [
    {
      "symbol": "NVDA",
      "target_score": 0.91,
      "sector_regime_fit": 0.94,
      "etf_holding_exposure": {"SMH": 0.20, "XLK": 0.12, "QQQ": 0.08},
      "relative_strength_score": 0.88,
      "optionability_score": 0.95,
      "event_risk_score": 0.32,
      "candidate_reason": ["core holding of strong semiconductor ETFs", "outperforming SMH and QQQ", "high option liquidity"]
    }
  ],
  "short_candidates": [],
  "excluded_candidates": [
    {"symbol": "ABC", "reason": "earnings within 24 hours"},
    {"symbol": "DEF", "reason": "option spread too wide"}
  ]
}
```

### Data organization implication

This layer creates a direct need for two data products:

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
  "symbol": "QQQ",
  "direction": "long",
  "layer_1_regime": {
    "state_name": "high_vol_risk_off",
    "confidence": 0.67,
    "transition_risk": 0.42
  },
  "layer_2_security_selection": {
    "target_score": 0.91,
    "preferred_sector_etfs": ["SMH", "XLK", "QQQ"],
    "candidate_reason": ["core holding of strong semiconductor ETFs", "high option liquidity"]
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
    "target_price": 455.0,
    "stop_price": 435.0,
    "expected_holding_days": 4
  },
  "layer_5_option_expression": {
    "structure": "long_call",
    "contracts": ["QQQ 2026-05-15 445C"],
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

- ETF holdings exposure matrix
- `stock_etf_exposure` derived table proposal
- full-market scan candidate logic
- long/short/watch/excluded candidate pools
- optionability and liquidity filters
- sector/style transmission evidence from ETF regime scores to stocks

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

1. What exact ETF basket and base equity universe should `SecuritySelectionModel` use first?
2. What is the first tradable universe for Phase 1 and Phase 2? ETF basket only, liquid mega-cap equities, or both?
3. What timestamp fields should be globally registered for model-facing event/evidence rows: `event_time`, `available_time`, `tradeable_time`, and ET/UTC variants?
4. What is the first label horizon for underlying trades: intraday, 1D, 5D, 10D, or multi-horizon?
5. Should `stock_etf_exposure` be registered as a derived data kind in `trading-manager`, or remain model-local until SecuritySelectionModel proves useful?
6. Should Phase 1 produce only offline research artifacts, or also a ready-signal contract for later execution systems?
