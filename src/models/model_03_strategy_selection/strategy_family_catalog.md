# StrategySelectionModel strategy family catalog

Status: Draft contract for review.

This catalog owns the Layer 3 standalone strategy-family summary for `StrategySelectionModel`. It is intentionally model-local until the family names, parameter gradients, and variant counts are accepted and promoted through `trading-manager`.

## Boundary

Layer 3 evaluates **single anonymous target candidates** and emits strategy setup fit. It does not choose final trade instructions.

Layer 3 may output:

- strategy group/family/variant;
- direction and horizon preference;
- setup-fit score and rank;
- eligibility state and reason codes;
- parameter-neighborhood stability and robustness evidence.

Layer 3 must not output:

- exact entry/exit order instructions;
- option DTE, strike, delta, premium, IV/Greeks, or contract ID;
- position size, portfolio weight, two-leg hedge ratio, or execution policy.

## Catalog summary

| Family | Group | Basic idea | Best-fit trading periods | Variant count | Alpaca data support |
|---|---|---|---|---:|---|
| `moving_average_crossover` | `trend_following` | Follow trend changes when a faster moving average crosses a slower one. | 30-minute, hourly, daily; weekly can be derived from daily bars for slower research. | 288 | `equity_bar` |
| `donchian_channel_breakout` | `trend_following` | Follow price when it breaks a prior high/low channel. | 15-minute, 30-minute, hourly, daily. | 288 | `equity_bar` |
| `macd_trend` | `trend_following` | Use MACD line/signal/histogram behavior to detect trend acceleration or reversal. | 15-minute, 30-minute, hourly, daily. | 288 | `equity_bar` |
| `bollinger_band_reversion` | `mean_reversion` | Fade stretched prices back toward a volatility band center when context supports reversion. | 15-minute, 30-minute, hourly, daily. | 384 | `equity_bar` |
| `rsi_reversion` | `mean_reversion` | Fade overbought/oversold momentum extremes, optionally requiring divergence or higher-timeframe confirmation. | 15-minute, 30-minute, hourly, daily. | 288 | `equity_bar` |
| `bias_reversion` | `mean_reversion` | Fade large deviations from a moving average or z-score baseline. | 15-minute, 30-minute, hourly, daily. | 384 | `equity_bar` |
| `vwap_reversion` | `mean_reversion` | Fade intraday price deviations back toward regular-session VWAP. | Minute-level / intraday only; default signal grains are 1-minute and 5-minute. | 216 | `equity_bar`; preferred `equity_liquidity_bar` |
| `range_breakout` | `breakout_volatility` | Trade a confirmed escape from a recent consolidation range. | 15-minute, 30-minute, hourly, daily. | 432 | `equity_bar`; optional `equity_liquidity_bar` |
| `opening_range_breakout` | `breakout_volatility` | Trade a regular-session break above/below the opening range. | Minute-level / morning intraday only; 1-minute bars required. | 48 | `equity_bar`; optional `equity_liquidity_bar` |
| `volatility_breakout` | `breakout_volatility` | Trade when volatility expands enough to suggest a new directional move. | 15-minute, 30-minute, hourly, daily. | 240 | `equity_bar`; optional `equity_liquidity_bar` |

Moved out of Layer 3 standalone implementation:

- `cross_sectional_momentum` — belongs with position/portfolio management because it ranks a universe and controls rebalance/turnover.
- `pairs_statistical_arbitrage` — belongs with position/portfolio management because it owns pair construction, hedge ratio, two-leg sizing, and spread risk.

Deferred final goals:

- `supervised_direction_classifier` — keep as the eventual supervised ML direction model after deterministic labels/baselines mature.
- `reinforcement_learning_policy` — keep as the eventual policy-learning target after simulator/reward/action validation matures.

## Variant counting rules

- `variant_count` is the product of listed variable axes unless a curated tuple axis is explicitly named.
- Fixed/default fields do not multiply variants.
- The hard ceiling remains 500 variants per standalone family unless a later review accepts an exception.
- Variant IDs should be generated from a canonical JSON spec and stable hash.
- Grids are intentionally sparse: variant differences must be large enough to survive costs, spread, slippage, and market noise.

## Standalone strategy families

### `moving_average_crossover`

Basic introduction: trend-following baseline. A bullish setup appears when a fast moving average crosses above a slow moving average; bearish is the inverse. It is simple, interpretable, and useful as a benchmark for more complex trend families.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute for liquid names with strict liquidity gates.
- Slower research: weekly can be derived from daily bars, but is not an option-oriented default.

Fixed parameters:

| Parameter | Value |
|---|---|
| `price_field` | `bar_close` |
| `exit_rule` | `opposite_cross_or_score_decay` |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `30Min`, `1Hour`, `1Day` | 3 |
| `ma_pair` | `(5,20)`, `(10,30)`, `(20,50)`, `(50,200)` | 4 |
| `ma_type` | `sma`, `ema` | 2 |
| `crossover_confirmation_bars` | `1`, `2`, `3` | 3 |
| `min_slope` | `0`, `0.05` | 2 |
| `trend_filter_enabled` | `false`, `true` | 2 |

Variant count: `3 * 4 * 2 * 3 * 2 * 2 = 288`.

Implementation notes:

- Enforce `fast_window < slow_window` through curated `ma_pair` values.
- This family should be a trend baseline, not the final strategy selector by itself.

### `donchian_channel_breakout`

Basic introduction: trend/breakout family based on prior high/low channels. It attempts to catch persistent moves after price exits a historical range.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute for liquid names with confirmation.
- Weekly can be derived for slow trend research, but is not a first option-oriented target.

Fixed parameters:

| Parameter | Value |
|---|---|
| `breakout_side` | `both` |
| `atr_window` | `14` |
| `retest_allowed` | `false` initially |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `entry_channel_window` | `20`, `55` | 2 |
| `exit_channel_window` | `10`, `20` | 2 |
| `breakout_buffer_atr` | `0`, `0.25`, `0.5` | 3 |
| `confirmation_bars` | `1`, `2` | 2 |
| `stop_atr_multiple` | `1.5`, `2.5`, `3.5` | 3 |

Variant count: `4 * 2 * 2 * 3 * 2 * 3 = 288`.

Implementation notes:

- `stop_atr_multiple` is setup/invalidation context only; actual order stops belong downstream.
- Daily variants need enough history before producing eligible state.

### `macd_trend`

Basic introduction: trend-following and momentum-confirmation family using MACD line, signal line, and histogram behavior.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute for liquid names.
- Avoid ultra-short 1-minute variants at first because MACD becomes noisy and option spreads magnify false signals.

Fixed parameters:

| Parameter | Value |
|---|---|
| `price_field` | `bar_close` |
| `trend_filter_window` | inherited from variant context if enabled later |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `macd_spec` | `(12,26,9)`, `(8,21,5)`, `(19,39,9)` | 3 |
| `histogram_threshold` | `0`, `0.25_atr_normalized` | 2 |
| `zero_line_filter` | `false`, `true` | 2 |
| `slope_confirmation_bars` | `1`, `2`, `3` | 3 |
| `exit_on_signal_cross` | `false`, `true` | 2 |

Variant count: `4 * 3 * 2 * 2 * 3 * 2 = 288`.

Implementation notes:

- `macd_spec` expands to `fast_ema_window`, `slow_ema_window`, and `signal_window`.
- Normalize histogram thresholds where possible so symbols with different price scales are comparable.

### `bollinger_band_reversion`

Basic introduction: mean-reversion family. It looks for price stretched toward/outside a volatility band and scores whether return toward the center is plausible.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute for liquid names with strict trend filters.
- Less suitable for weekly option-targeted work because signal frequency is too low.

Fixed parameters:

| Parameter | Value |
|---|---|
| `price_field` | `bar_close` |
| `rsi_filter_period` | optional diagnostic only initially |
| `volatility_regime_filter` | `allowed_unless_extreme_trend` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `window` | `20`, `30` | 2 |
| `band_stddev` | `1.5`, `2.0`, `2.5` | 3 |
| `entry_band` | `outer_touch`, `close_outside` | 2 |
| `exit_band` | `midline`, `half_sigma` | 2 |
| `trend_filter_enabled` | `false`, `true` | 2 |
| `max_hold_bars` | `10`, `20` | 2 |

Variant count: `4 * 2 * 3 * 2 * 2 * 2 * 2 = 384`.

Implementation notes:

- Trend filter is important: this family should avoid fading strong one-way trend regimes without extra evidence.
- `max_hold_bars` is an evaluation/setup expiry concept, not an execution instruction.

### `rsi_reversion`

Basic introduction: mean-reversion family based on overbought/oversold momentum. It can optionally require divergence or multi-timeframe confirmation.

Suitable trading periods:

- Best: 15-minute, 30-minute, hourly, daily.
- Minute-level use below 15-minute should wait until liquidity/cost evidence is strong.

Fixed parameters:

| Parameter | Value |
|---|---|
| `price_field` | `bar_close` |
| `max_hold_bars` | family default by timeframe |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `rsi_period` | `7`, `14`, `21` | 3 |
| `threshold_pair` | `(30,70)`, `(25,75)`, `(20,80)` | 3 |
| `exit_midline` | `45_55_band`, `50_cross` | 2 |
| `divergence_required` | `false`, `true` | 2 |
| `multi_timeframe_confirm` | `false`, `true` | 2 |

Variant count: `4 * 3 * 3 * 2 * 2 * 2 = 288`.

Implementation notes:

- `threshold_pair` expands to `oversold_threshold` and `overbought_threshold`.
- Divergence detection must be deterministic and point-in-time; avoid post-hoc swing-point leakage.

### `bias_reversion`

Basic introduction: mean-reversion family based on distance from a moving average or z-score baseline. It is a direct measure of price stretch.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute with strict liquidity and trend filters.

Fixed parameters:

| Parameter | Value |
|---|---|
| `price_field` | `bar_close` |
| `max_hold_bars` | family default by timeframe |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `ma_window` | `20`, `50` | 2 |
| `ma_type` | `sma`, `ema` | 2 |
| `deviation_measure` | `pct_from_ma`, `zscore_from_ma` | 2 |
| `entry_deviation_threshold` | `1.5`, `2.0`, `2.5` | 3 |
| `exit_deviation_threshold` | `0.25`, `0.5` | 2 |
| `trend_filter_enabled` | `false`, `true` | 2 |

Variant count: `4 * 2 * 2 * 2 * 3 * 2 * 2 = 384`.

Implementation notes:

- If `deviation_measure = pct_from_ma`, thresholds should be interpreted as percent/bps families; if z-score, thresholds are standard-deviation units.
- Keep threshold semantics explicit in the variant payload.

### `vwap_reversion`

Basic introduction: intraday mean-reversion family. It looks for a liquid underlying moving too far from regular-session VWAP and scores whether reversion is plausible before the option trade window decays.

Suitable trading periods:

- Best: minute-level / intraday.
- Default signal grains: 1-minute and 5-minute.
- Not suitable for daily/weekly variants.

Fixed parameters:

| Parameter | Value |
|---|---|
| `vwap_scope` | `regular_session_vwap` |
| `premarket_context_mode` | `context_filter` |
| `earliest_entry_time` | `10:00 ET` |
| `no_trade_after_time` | `15:30 ET` |
| `minimum_dollar_volume` | `target_relative_liquidity_gate` |
| `time_of_day_bucket` | derived label, not a variant axis |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `signal_timeframe` | `1Min`, `5Min` | 2 |
| `deviation_bps` | `30`, `50`, `75`, `100` | 4 |
| `entry_zscore` | `1.0`, `1.5`, `2.0` | 3 |
| `exit_zscore` | `0.25`, `0.5`, `0.75` | 3 |
| `maximum_spread_bps` | `5`, `10`, `15` | 3 |

Variant count: `2 * 4 * 3 * 3 * 3 = 216`.

Implementation notes:

- `minimum_dollar_volume` must be target-relative, e.g. current-window dollar volume versus rolling median/percentile for the same target and timeframe.
- `time_of_day_bucket` is derived from `available_time` for diagnostics and calibration; do not let it multiply variants initially.
- Option chain and contract liquidity checks belong to `OptionExpressionModel`.

### `range_breakout`

Basic introduction: breakout family that looks for price escaping a recent consolidation range with enough confirmation to avoid wick-only false breaks.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute with volume/liquidity confirmation.

Fixed parameters:

| Parameter | Value |
|---|---|
| `breakout_direction` | `both` |
| `close_confirmation` | `true` |
| `failed_breakout_timeout` | family default by timeframe |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `range_lookback` | `20`, `40`, `60` | 3 |
| `range_width_max_atr` | `1.0`, `1.5`, `2.0` | 3 |
| `breakout_buffer_atr` | `0`, `0.25`, `0.5` | 3 |
| `volume_confirmation_ratio` | `1.0`, `1.5` | 2 |
| `retest_rule` | `none`, `allow_once` | 2 |

Variant count: `4 * 3 * 3 * 3 * 2 * 2 = 432`.

Implementation notes:

- Range width cap prevents labeling already-expanded moves as range breaks.
- `retest_rule` should remain setup evidence, not a downstream order instruction.

### `opening_range_breakout`

Basic introduction: morning intraday breakout family. It defines the regular-session opening range and scores a confirmed move above or below it.

Suitable trading periods:

- Best: minute-level / morning intraday.
- Requires 1-minute bars for opening range construction.
- Not suitable for daily/weekly variants.

Fixed parameters:

| Parameter | Value |
|---|---|
| `regular_session_open` | `09:30 ET` |
| `direction_mode` | `both` |
| `first_trade_delay_minutes` | `5` |
| `time_stop_minutes` | `60` |
| `max_trades_per_session` | `1` |
| `premarket_context_mode` | `context_filter` |
| `no_trade_after_time` | `11:00 ET` |
| `liquidity_filter` | `strict` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `opening_range_minutes` | `5`, `15`, `30`, `60` | 4 |
| `breakout_buffer_bps` | `5`, `10`, `20` | 3 |
| `volume_confirmation_ratio` | `1.0`, `1.25`, `1.5`, `2.0` | 4 |

Variant count: `4 * 3 * 4 = 48`.

Implementation notes:

- Premarket can filter context but must not define the opening range.
- One signal per target/session is the starting rule; repeated breakouts usually imply chop and are costly for option trades.

### `volatility_breakout`

Basic introduction: breakout/volatility family. It scores whether volatility expansion is large enough to suggest a tradable move, then uses a direction filter to avoid directionless noise.

Suitable trading periods:

- Best: 30-minute, hourly, daily.
- Usable: 15-minute with strict liquidity gates.

Fixed parameters:

| Parameter | Value |
|---|---|
| `cooldown_bars` | `1` |
| `volatility_cooloff_threshold` | family default by timeframe |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `timeframe` | `15Min`, `30Min`, `1Hour`, `1Day` | 4 |
| `volatility_spec` | `ATR14_x1.25`, `ATR14_x1.5`, `ATR20_x1.5`, `HV20_x1.5`, `HV30_x2.0` | 5 |
| `direction_filter` | `none`, `trend`, `range_break` | 3 |
| `confirmation_bars` | `1`, `2` | 2 |
| `stop_atr_multiple` | `1.5`, `2.5` | 2 |

Variant count: `4 * 5 * 3 * 2 * 2 = 240`.

Implementation notes:

- `volatility_spec` expands to `volatility_measure`, `volatility_window`, and `expansion_threshold`.
- A volatility breakout without direction filter should be evaluated cautiously; expansion alone does not guarantee directional edge.

## Modifier and meta families

These should not blindly multiply every standalone family variant. Apply them only through reviewed experiments, otherwise variant count explodes and interpretation degrades.

### `trend_volatility_filter`

Basic introduction: reusable filter/modifier that permits or scores trend strategies only when trend and volatility conditions are suitable.

Suitable periods: same as the strategy family it modifies; usually 30-minute, hourly, and daily.

Potential gradients:

| Axis | Values |
|---|---|
| `trend_window` | `20`, `50` |
| `trend_slope_min` | `0`, `0.05` |
| `volatility_measure` | `ATR`, `HV` |
| `volatility_window` | `14`, `20` |
| `volatility_min_percentile` | `none`, `20` |
| `volatility_max_percentile` | `80`, `95` |
| `filter_mode` | `gate`, `score_adjustment` |

Potential standalone config count: `2 * 2 * 2 * 2 * 2 * 2 * 2 = 128`, but it should not be globally multiplied into all families.

### `mean_reversion_trend_filter`

Basic introduction: reusable filter/modifier that permits mean reversion only under acceptable higher-timeframe trend and pullback conditions.

Suitable periods: same as the mean-reversion family it modifies; higher timeframe should be one level above the signal timeframe where possible.

Potential gradients:

| Axis | Values |
|---|---|
| `higher_timeframe` | `30Min`, `1Hour`, `1Day` |
| `higher_timeframe_trend_window` | `20`, `50` |
| `allowed_trend_states` | `with_trend_pullback`, `range_only`, `any_non_extreme` |
| `pullback_depth_min` | `0.5_atr`, `1.0_atr` |
| `pullback_depth_max` | `2.0_atr`, `3.0_atr` |
| `filter_mode` | `gate`, `score_adjustment` |

Potential standalone config count: `3 * 2 * 3 * 2 * 2 * 2 = 144`, but it should not be globally multiplied into all families.

### `multi_factor_scoring`

Basic introduction: meta-family for combining deterministic family evidence into a score after individual families have stable labels, baselines, and reliability diagnostics.

Suitable periods: daily and intraday once deterministic family outputs exist. It is not a first standalone signal family.

Potential gradients:

| Axis | Values |
|---|---|
| `factor_set_id` | reviewed deterministic family feature set |
| `factor_weights` | equal, learned_regularized, regime_conditioned |
| `normalization_method` | zscore, rank, robust_percentile |
| `score_window` | 20, 60, 120 |
| `rank_method` | absolute_score, within_sector, within_candidate_bucket |
| `minimum_score` | reviewed threshold grid |
| `turnover_penalty` | off, standard, strict |
| `correlation_penalty` | off, standard, strict |

Variant count is intentionally not assigned yet because this family depends on accepted deterministic output surfaces and should not be implemented before those surfaces exist.

## Deferred final goals

### `supervised_direction_classifier`

Basic introduction: supervised ML classifier/regressor that predicts future direction or return bucket from accepted features and deterministic family evidence.

Suitable periods: depends on label design; likely 30-minute, hourly, daily first, with minute-level only after cost/slippage evidence matures.

Deferred because it requires mature labels, train/validation splits, probability calibration, baseline comparisons, and leakage checks.

### `reinforcement_learning_policy`

Basic introduction: policy-learning target that learns actions in a simulated trading environment.

Suitable periods: not selected yet. It depends on simulator design, action space, transaction-cost model, reward function, and offline validation protocol.

Deferred because it is too easy to overfit or learn non-executable behavior before deterministic baselines and execution/cost models are mature.

## Additional items needed before implementation

1. **Canonical strategy spec schema** — JSON schema for fixed fields, variable axes, variant IDs, and stable spec hash.
2. **Variant generator** — deterministic generator that expands only reviewed axes and enforces constraints.
3. **Period/calendar policy** — regular-session calendar, aggregation rules, weekly-from-daily derivation, and timezone handling.
4. **Liquidity policy** — target-relative dollar-volume gates, quote-count gates, and spread bps gates.
5. **Cost/slippage assumptions** — underlying spread/cost evidence at Layer 3, with option-specific costs deferred to `OptionExpressionModel`.
6. **Label definitions** — future setup-success labels that evaluate setup quality without leaking future trade-management decisions.
7. **Baseline comparison** — family-specific baseline and market/sector/candidate-only baseline.
8. **Stability gates** — split/refit stability, parameter-neighborhood stability, and variant-family robustness.
9. **Anonymity checks** — ensure strategy variants consume anonymous target features and reviewed context, not raw ticker/company identity.
10. **Promotion path** — no family becomes production-active until real-data evaluation and promotion review are accepted.
