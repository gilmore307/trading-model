# RFC: Six-Layer Trading Model Architecture

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
2. StrategySelectionModel (`strategy_selection_model`)
  ↓
3. TradeQualityModel (`trade_quality_model`)
  ↓
4. OptionExpressionModel (`option_expression_model`)
  ↓
5. EventOverlayModel (`event_overlay_model`)
  ↓
6. PortfolioRiskModel (`portfolio_risk_model`)
```

Layer 5 and Layer 6 are not simple downstream stages:

- **Layer 5 is an overlay** that can modify Layers 1-4 and the final risk gate.
- **Layer 6 is the final execution gate** and can reject, resize, delay, or alter any candidate trade.

The system should not answer only “buy or sell.” It should answer:

- What market state are we in?
- Which strategy family is appropriate in this state?
- Is this signal worth trading?
- What target, stop, holding time, and adverse/favorable excursion are expected?
- Should the trade be expressed with stock, ETF, option, or an option spread?
- Is there event risk or event opportunity?
- Does the current portfolio allow this trade?
- What size, execution style, and exit plan should be used?

## Canonical Layer Names

These names are canonical for docs, code, artifact metadata, and future registry proposals. Use the `stable id` in machine-facing paths/configs and the `model class` name in code/docs where PascalCase is appropriate.

| Layer | Model class | Stable id | Chinese name | Role |
|---|---|---|---|---|
| 1 | `MarketRegimeModel` | `market_regime_model` | 市场状态模型 | Detect point-in-time market regime, state probabilities, confidence, transition risk, and dominant drivers. |
| 2 | `StrategySelectionModel` | `strategy_selection_model` | 策略选择模型 | Select strategy family/variant conditioned on regime, symbol, cost, and robustness evidence. |
| 3 | `TradeQualityModel` | `trade_quality_model` | 交易质量模型 | Score candidate signals and predict trade outcome distribution, target/stop, MFE/MAE, and holding horizon. |
| 4 | `OptionExpressionModel` | `option_expression_model` | 期权表达模型 | Choose stock/ETF/option/option-spread expression from signal forecast, option chain, liquidity, IV, and Greeks. |
| 5 | `EventOverlayModel` | `event_overlay_model` | 事件覆盖模型 | Overlay scheduled/breaking event risk, abnormal activity, and event-memory adjustments across earlier layers and the risk gate. |
| 6 | `PortfolioRiskModel` | `portfolio_risk_model` | 组合风控模型 | Final offline risk, sizing, exposure, execution-gate, exit-rule, and kill-switch model. |

Naming rule: do not call Layer 6 simply `ExecutionModel`, because live/paper order placement is outside `trading-model`. `PortfolioRiskModel` may describe execution-gate logic but does not mutate brokerage state.

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

The accepted `trading-model` scope is now the full six-layer offline modeling architecture. Implementation should still stay phased, with `MarketRegimeModel` as the likely first slice.

Recommended ownership split:

| Area | Likely owner |
|---|---|
| Source acquisition, source-evidence bundles | `trading-data` |
| Shared fields, identifiers, contracts, registry | `trading-main` |
| Offline model research and validation | `trading-model` |
| Scheduling/routing/lifecycle | `trading-manager` / execution-side repos |
| Live execution, order placement, broker integration | execution/risk repository, not `trading-model` |

If a later decision splits one or more layers into separate component repositories, update `docs/00_scope.md`, this RFC, and `trading-main` registry/contracts together.

## Layer 1: MarketRegimeModel

### Goal

Identify current market regime using market-only features.

The model should capture:

- risk appetite
- volatility state
- rate environment
- dollar pressure
- commodity rotation
- sector rotation
- market breadth
- cross-asset correlation
- trend strength
- transition risk

### Inputs

Primary ETF/cross-asset basket:

```text
SPY, QQQ, IWM, DIA, RSP
XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLU, XLB
TLT, IEF, SHY, HYG, LQD
GLD, SLV, USO, DBC
UUP
VIX/VIX proxy/VIXY/SVXY as available
EFA, EEM, FXI
```

Useful ratios:

```text
SPY/TLT, QQQ/SPY, IWM/SPY, HYG/LQD, RSP/SPY,
XLK/XLP, XLY/XLP, GLD/SPY, UUP/SPY
```

### Feature families

- returns: 1D, 5D, 10D, 20D, 60D
- realized volatility and volatility-of-volatility
- ATR and range features
- moving-average slope, ADX, momentum
- ETF/cross-asset rolling correlations
- market breadth proxies such as RSP/SPY and sector participation
- credit risk: HYG/LQD, HYG/TLT
- rate risk: TLT/SHY, IEF/SHY
- safe-haven demand: GLD/SPY, TLT/SPY
- dollar pressure: UUP and cross-relations
- recent regime-probability changes

### First model methods

Start simple and interpretable:

```text
rolling/expanding scaler
+ PCA/factor compression
+ Gaussian Mixture Model or HMM
+ human-readable regime naming
```

Avoid using full-history clustering to label the past.

### Output contract sketch

```json
{
  "timestamp": "2026-04-28T09:30:00-04:00",
  "state_id": 2,
  "state_name": "high_vol_risk_off",
  "state_probabilities": {
    "low_vol_risk_on": 0.08,
    "range_bound": 0.14,
    "high_vol_risk_off": 0.67,
    "inflation_rotation": 0.07,
    "rate_shock": 0.04
  },
  "confidence": 0.67,
  "transition_risk": 0.42,
  "dominant_drivers": ["VIX_up", "HYG_underperforming_LQD", "QQQ_underperforming_SPY"],
  "expected_volatility_level": "high",
  "expected_correlation_level": "high"
}
```

### Evaluation

- regime stability
- transition detection usefulness
- interpretability
- strategy-performance separation by regime
- drawdown warning usefulness

## Layer 2: StrategySelectionModel

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

## Layer 3: TradeQualityModel

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

## Layer 4: OptionExpressionModel

### Goal

Choose the best trading expression after Layer 3 produces expected underlying move, target, stop, and holding horizon.

V1 allowed structures:

- long call
- long put
- call debit spread
- put debit spread

Defer complex structures until risk/margin and backtest realism are mature:

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

## Layer 5: EventOverlayModel

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

Layer 5 can:

- raise Layer 1 transition risk
- disable Layer 2 strategy families
- reduce Layer 3 signal quality
- alter Layer 4 DTE/structure/vega constraints
- force Layer 6 size reduction, no-trade, or kill-switch behavior

### Information-leakage risk

Never train pre-event models using post-event explanations. Every event row must preserve observable timing and source priority.

## Layer 6: PortfolioRiskModel

### Goal

Decide whether a candidate trade may be placed, at what size, through what execution style, and under what exit plan.

Inputs include:

- Layer 1 regime/confidence
- Layer 2 strategy recommendation
- Layer 3 signal quality
- Layer 4 option structure/liquidity
- Layer 5 event risk/opportunity
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
  "layer_2_strategy": {
    "family": "breakdown_trend_following",
    "variant_id": "BT_12_3ATR_5D",
    "strategy_score": 0.74
  },
  "layer_3_signal_quality": {
    "trade_quality_score": 0.72,
    "probability_of_profit": 0.58,
    "expected_return": 0.024,
    "target_price": 455.0,
    "stop_price": 435.0,
    "expected_holding_days": 4
  },
  "layer_4_option_selection": {
    "structure": "call_debit_spread",
    "contracts": ["QQQ 2026-05-15 445C", "QQQ 2026-05-15 455C"],
    "expected_option_pnl": 1.35,
    "max_loss": 3.2,
    "liquidity_score": 0.88,
    "option_score": 0.76
  },
  "layer_5_event_overlay": {
    "event_risk_score": 0.38,
    "event_type": "none_major",
    "action": "normal"
  },
  "layer_6_risk_execution": {
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

Do not build all six layers at once.

### Phase 1: Data foundation + Layer 1

Deliver:

- market-state feature dataset contract
- rolling/expanding regime model prototype
- regime probability and transition-risk outputs
- regime dashboard/data artifact sketch
- per-regime market behavior statistics
- first evidence that regimes are stable, interpretable, and useful

### Phase 2: Layer 2 strategy library

Deliver:

- small strategy-family library
- limited variants
- regime-conditioned performance table
- disabled strategy list
- parameter-neighborhood stability evidence

### Phase 3: Layer 3 signal quality model

Deliver:

- underlying-only trade labels
- triple-barrier labeling implementation
- trade quality score
- expected return / target / stop / holding-time outputs
- score-decile performance evidence

### Phase 4: Layer 4 option selector

Deliver:

- option-chain snapshot feature contract
- long call/put and debit-spread ranker
- liquidity/IV/crush filters
- expected option PnL and fill/slippage assumptions

### Phase 5: Layer 5 event overlay

Deliver:

- scheduled event risk score
- earnings IV-crush model
- macro event risk model
- abnormal option/price/volume activity detector
- overlay adjustment rules for Layers 1-4 and Layer 6

### Phase 6: Layer 6 risk/execution gate

Deliver:

- position sizing engine
- exposure monitor
- order/execution rules
- exit lifecycle rules
- kill switch
- PnL and attribution dashboard contract

## Immediate Next Design Questions

Before implementation, decide:

1. Does `trading-model` expand from market-state-only to the full six-layer offline modeling repository, or do Layers 2-6 get separate component owners?
2. What is the first tradable universe for Phase 1 and Phase 2? ETF basket only, liquid mega-cap equities, or both?
3. What timestamp fields should be globally registered for model-facing event/evidence rows: `event_time`, `available_time`, `tradeable_time`, and ET/UTC variants?
4. What is the first label horizon for underlying trades: intraday, 1D, 5D, 10D, or multi-horizon?
5. Should Phase 1 produce only offline research artifacts, or also a ready-signal contract for later execution systems?
