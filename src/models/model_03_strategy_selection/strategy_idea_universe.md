# StrategySelectionModel strategy idea universe

Status: Draft idea registry.

This file is intentionally broader than the first implementation catalog. It records strategy families and near-families we may want to evaluate later, even when they are not ready for implementation. Each idea must carry an ownership/status label so the project does not accidentally implement portfolio, execution, event, option-expression, or ML policy logic inside Layer 3.

## Status vocabulary

| Status | Meaning |
|---|---|
| `layer3_catalog` | Already in `strategy_family_catalog.md` as a standalone Layer 3 family. |
| `layer3_backlog` | Plausible future standalone Layer 3 family, pending design/evidence review. |
| `modifier` | Reusable filter or score adjustment, not a standalone strategy family by default. |
| `meta_family` | Composition/scoring/ensemble layer over other families. |
| `position_management` | Better owned by target selection, position sizing, pair/portfolio construction, or allocation. |
| `option_expression` | Better owned by `OptionExpressionModel` because it selects option contracts/structures. |
| `execution` | Better owned by execution/microstructure logic. |
| `event_or_overlay` | Requires event/news/macro/on-chain overlay and is not part of the current Layer 3 standalone catalog. |
| `deferred_ml_rl` | Retained final-goal ML/RL direction, but not implemented before deterministic baselines mature. |
| `removed` | Explicitly excluded from this catalog unless a later accepted architecture reopens the boundary. |

## Current Layer 3 standalone catalog

| Group | Family | Status | Notes |
|---|---|---|---|
| `trend_following` | `moving_average_crossover` | `layer3_catalog` | MA cross trend baseline. |
| `trend_following` | `donchian_channel_breakout` | `layer3_catalog` | Channel breakout trend family. |
| `trend_following` | `macd_trend` | `layer3_catalog` | MACD trend/momentum confirmation. |
| `mean_reversion` | `bollinger_band_reversion` | `layer3_catalog` | Volatility-band reversion. |
| `mean_reversion` | `rsi_reversion` | `layer3_catalog` | RSI overbought/oversold reversion. |
| `mean_reversion` | `bias_reversion` | `layer3_catalog` | Distance-from-average reversion. |
| `mean_reversion` | `vwap_reversion` | `layer3_catalog` | Intraday regular-session VWAP reversion. |
| `breakout_volatility` | `range_breakout` | `layer3_catalog` | Consolidation/range escape. |
| `breakout_volatility` | `opening_range_breakout` | `layer3_catalog` | Morning opening-range breakout. |
| `breakout_volatility` | `volatility_breakout` | `layer3_catalog` | ATR/HV expansion with direction filter. |

## Layer 3 backlog candidates

These may become future standalone Layer 3 families if they can be defined as single-candidate setup classifiers with point-in-time Alpaca-compatible evidence.

### Trend / continuation backlog

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `adx_trend_strength` | `layer3_backlog` | Use ADX/DMI to score trend strength and direction. | OHLC-derived; good candidate. |
| `parabolic_sar_trend` | `layer3_backlog` | Follow PSAR flips/trailing trend state. | OHLC-derived; may overlap MA/MACD. |
| `supertrend_following` | `layer3_backlog` | ATR-band trend state and flips. | OHLC-derived; useful option-friendly trend filter/family. |
| `ichimoku_trend` | `layer3_backlog` | Cloud/trend/tenkan-kijun confirmation. | OHLC-derived but parameter-heavy; avoid overfitting. |
| `price_above_moving_average_stack` | `layer3_backlog` | Score ordered MA stack / trend alignment. | Similar to MA crossover; may be modifier instead. |
| `higher_high_higher_low_trend` | `layer3_backlog` | Detect swing structure continuation. | Needs point-in-time swing definition. |
| `pullback_to_moving_average_continuation` | `layer3_backlog` | Trend continuation after pullback to MA/VWAP. | Good option setup candidate. |
| `relative_strength_vs_benchmark` | `layer3_backlog` | Single target out/underperformance versus SPY/sector benchmark. | Not cross-sectional allocation if used as target-local feature/family. |
| `trend_day_continuation` | `layer3_backlog` | Intraday trend day detection and continuation. | Intraday/session evidence; option-friendly. |
| `anchored_vwap_trend_continuation` | `layer3_backlog` | Trend continuation around anchored VWAP from event/session high/low. | Needs reviewed anchor rules. |

### Mean-reversion backlog

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `keltner_channel_reversion` | `layer3_backlog` | Revert from ATR channel extremes. | OHLC-derived; complements Bollinger. |
| `cci_reversion` | `layer3_backlog` | Commodity Channel Index overextension reversion. | OHLC-derived. |
| `stochastic_reversion` | `layer3_backlog` | Stochastic oscillator overbought/oversold reversion. | OHLC-derived. |
| `williams_r_reversion` | `layer3_backlog` | Williams %R overextension reversion. | OHLC-derived. |
| `zscore_return_reversion` | `layer3_backlog` | Revert statistically unusual returns. | Bar-derived; needs volatility scaling. |
| `gap_fade` | `layer3_backlog` | Fade opening gap toward prior close/VWAP. | Intraday + prior close; must manage trend-day risk. |
| `failed_breakout_reversion` | `layer3_backlog` | Fade breakouts that fail back inside range. | Requires deterministic false-break rule. |
| `vwap_band_reversion` | `layer3_backlog` | Revert from VWAP bands rather than raw VWAP distance. | Intraday liquidity/session evidence. |
| `support_resistance_reversion` | `layer3_backlog` | Revert at reviewed support/resistance zones. | Needs point-in-time level construction. |
| `overnight_gap_reversion` | `layer3_backlog` | Fade overnight gap after regular-session confirmation. | Requires session split; option spread at open must be handled. |

### Breakout / volatility backlog

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `keltner_channel_breakout` | `layer3_backlog` | Breakout beyond ATR channel. | OHLC-derived; complements Donchian/range. |
| `bollinger_band_breakout` | `layer3_backlog` | Volatility-band expansion continuation. | Must avoid conflict with Bollinger reversion. |
| `squeeze_breakout` | `layer3_backlog` | Bollinger/Keltner squeeze release. | OHLC-derived; promising option setup. |
| `nr7_breakout` | `layer3_backlog` | Breakout after narrowest range in 7 bars. | OHLC-derived. |
| `inside_bar_breakout` | `layer3_backlog` | Breakout from inside-bar compression. | OHLC-derived. |
| `gap_continuation` | `layer3_backlog` | Continue strong gap after confirmation. | Intraday/session evidence; distinct from gap fade. |
| `high_low_range_expansion` | `layer3_backlog` | Expansion of intraday high-low range vs baseline. | Bar-derived. |
| `volume_price_breakout` | `layer3_backlog` | Price breakout confirmed by relative volume. | Bar/liquidity-derived. |
| `atr_trailing_breakout` | `layer3_backlog` | Directional break with ATR trailing invalidation. | Layer 3 can score setup; exits downstream. |
| `opening_drive_continuation` | `layer3_backlog` | Strong first 30-60m opening drive continuation. | Intraday/session evidence. |

### Volume / liquidity / order-flow-style backlog

Alpaca supports trades/quotes, but raw rows should remain transient and be aggregated. These should use `equity_liquidity_bar` style evidence rather than raw tick persistence by default.

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `relative_volume_surge_continuation` | `layer3_backlog` | Continue moves with abnormal relative volume. | Bars/trades support. |
| `volume_climax_reversal` | `layer3_backlog` | Fade exhaustion after volume climax. | Needs robust climax definition. |
| `spread_compression_breakout` | `layer3_backlog` | Breakout after spread/liquidity improves. | Quotes/liquidity aggregates. |
| `spread_widening_risk_off` | `modifier` | Penalize setups when spread widens. | Better modifier/gate. |
| `trade_count_activity_surge` | `layer3_backlog` | Activity burst as confirmation signal. | Trades/liquidity aggregates. |
| `vwap_minus_mid_dislocation` | `layer3_backlog` | Score dislocation between trade VWAP and quote mid. | Alpaca liquidity feed can derive. |
| `quote_imbalance_pressure` | `layer3_backlog` | Use bid/ask size imbalance as pressure signal. | Requires quote aggregates; noisy. |
| `liquidity_vacuum_breakout` | `layer3_backlog` | Breakout when liquidity thins and price moves. | Needs careful slippage controls. |
| `dollar_volume_regime_filter` | `modifier` | Gate signals by target-relative dollar volume. | Already needed for intraday families. |
| `spread_bps_regime_filter` | `modifier` | Gate signals by spread bps. | Already needed for option-targeted setups. |

### Session / intraday pattern backlog

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `midday_range_breakout` | `layer3_backlog` | Breakout from lunchtime consolidation. | Intraday/session evidence. |
| `afternoon_trend_continuation` | `layer3_backlog` | Continue established afternoon trend before close cutoff. | Must respect option late-day rules. |
| `power_hour_breakout` | `layer3_backlog` | Late-day breakout/continuation. | Risky for options; likely strict/deferred. |
| `morning_reversal` | `layer3_backlog` | Fade first-hour extreme after confirmation. | Intraday/session evidence. |
| `lunch_reversion` | `layer3_backlog` | Revert midday overextension. | Intraday/session evidence. |
| `previous_day_high_low_break` | `layer3_backlog` | Break above/below previous day high/low. | Bar/session-derived. |
| `previous_close_gap_hold` | `layer3_backlog` | Gap holds above/below previous close and continues. | Session-derived. |
| `first_pullback_after_opening_drive` | `layer3_backlog` | Enter continuation after first pullback in trend day. | Needs deterministic pullback rules. |

### Pattern / candle-structure backlog

Use only if definitions are mechanical and point-in-time. Avoid discretionary chart-pattern drift.

| Family idea | Status | Basic idea | Data support / caveat |
|---|---|---|---|
| `engulfing_reversal` | `layer3_backlog` | Mechanical bullish/bearish engulfing reversal. | OHLC-derived; probably weak alone. |
| `pin_bar_reversal` | `layer3_backlog` | Wick rejection reversal. | OHLC-derived; needs filters. |
| `inside_outside_bar_pattern` | `layer3_backlog` | Inside/outside bar continuation or reversal. | OHLC-derived. |
| `three_bar_reversal` | `layer3_backlog` | Three-bar exhaustion/reversal. | OHLC-derived. |
| `breakaway_gap_pattern` | `layer3_backlog` | Gap plus follow-through pattern. | Session-derived. |
| `measured_move_continuation` | `layer3_backlog` | Follow proportional continuation after first leg. | Needs swing-point policy. |
| `support_resistance_break_retest` | `layer3_backlog` | Break and retest of mechanical level. | Needs level construction. |

### Relative / portfolio-like ideas

These should not become standalone Layer 3 single-candidate families unless narrowed into target-local evidence.

| Family idea | Status | Basic idea | Future owner direction |
|---|---|---|---|
| `cross_sectional_momentum` | `position_management` | Rank a universe by momentum and allocate to winners/losers. | Position/portfolio management. |
| `pairs_statistical_arbitrage` | `position_management` | Two-leg spread mean reversion. | Pair/portfolio management. |
| `sector_rotation_allocation` | `position_management` | Allocate among sectors based on rotation. | Portfolio allocation; Layer 2/3 can provide evidence. |
| `risk_parity_allocation` | `position_management` | Allocate by volatility/risk contribution. | Portfolio construction. |
| `volatility_targeting_overlay` | `position_management` | Adjust exposure based on realized vol. | Sizing/risk layer. |
| `kelly_fraction_sizing` | `position_management` | Size by edge/variance. | Position sizing; high risk if premature. |
| `anti_martingale_sizing_overlay` | `position_management` | Increase exposure after gains under controls. | Sizing/risk overlay only, not standalone. |

### Option-expression ideas

These are not Layer 3 family implementations. They may consume Layer 3 setup output later.

| Idea | Status | Basic idea | Owner |
|---|---|---|---|
| `long_call_expression` | `option_expression` | Express bullish setup as long call. | `OptionExpressionModel` |
| `long_put_expression` | `option_expression` | Express bearish setup as long put. | `OptionExpressionModel` |
| `debit_spread_expression` | `option_expression` | Express setup with capped-risk spread. | Future OptionExpression extension, not V1. |
| `iv_rank_filter` | `option_expression` | Gate option entry by IV context. | OptionExpression / risk. |
| `delta_bucket_selection` | `option_expression` | Choose contract delta/moneyness. | OptionExpression. |
| `dte_bucket_selection` | `option_expression` | Choose expiration horizon. | OptionExpression. |
| `theta_decay_filter` | `option_expression` | Avoid setups with poor time-decay tradeoff. | OptionExpression. |
| `option_liquidity_filter` | `option_expression` | Gate by option spread/open interest/volume. | OptionExpression. |

### Event / overlay ideas

Earlier decision removed event-driven families from the current Layer 3 standalone catalog. Keep ideas here only as future overlay candidates.

| Idea | Status | Basic idea | Owner direction |
|---|---|---|---|
| `earnings_gap_reaction` | `event_or_overlay` | React to earnings gap/volatility. | EventOverlay + OptionExpression later. |
| `earnings_iv_crush_avoidance` | `event_or_overlay` | Avoid long premium before IV crush. | OptionExpression/risk. |
| `macro_release_volatility_filter` | `event_or_overlay` | Gate around CPI/FOMC/NFP. | EventOverlay/risk. |
| `news_sentiment_reaction` | `event_or_overlay` | Use Alpaca/news sentiment features. | Deferred overlay/ML. |
| `analyst_rating_reaction` | `event_or_overlay` | React to analyst upgrades/downgrades. | Event data source required. |
| `sec_filing_reaction` | `event_or_overlay` | React to filings/8-K. | EventOverlay. |
| `halt_resume_pattern` | `event_or_overlay` | Handle halt/resume volatility. | Execution/risk first. |

### ML / RL final goals

| Family idea | Status | Basic idea | Gate before implementation |
|---|---|---|---|
| `supervised_direction_classifier` | `deferred_ml_rl` | Predict future direction/return bucket from accepted features. | Deterministic baselines, labels, leakage checks, calibration. |
| `supervised_strategy_selector` | `deferred_ml_rl` | Choose best deterministic family/variant for candidate. | Stable family outputs and promotion evidence. |
| `meta_labeling_filter` | `deferred_ml_rl` | Predict whether a deterministic signal should be taken. | Clean signal labels and baseline. |
| `probabilistic_return_forecaster` | `deferred_ml_rl` | Predict distribution/quantiles of returns. | Calibration and robust validation. |
| `reinforcement_learning_policy` | `deferred_ml_rl` | Learn actions in simulated trading environment. | Simulator, costs, rewards, offline validation. |

## Why keep this broad file separate?

`strategy_family_catalog.md` is the implementation-facing catalog. This file is the idea universe. New ideas can be added here without becoming implementation commitments. Promotion path should be:

```text
idea universe -> reviewed Layer 3 backlog candidate -> strategy_family_catalog entry -> spec schema + variant generator -> evaluation -> promotion review
```
