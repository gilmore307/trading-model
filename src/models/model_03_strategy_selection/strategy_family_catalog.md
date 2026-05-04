# StrategySelectionModel strategy family catalog

Status: Draft contract for review.

This catalog owns the Layer 3 standalone strategy-family summary for `StrategySelectionModel`. It is intentionally model-local until the family names, parameter gradients, and variant counts are accepted and promoted through `trading-manager`.

Implemented active standalone family specs live under `families/`, with one reviewed strategy family per numbered Python file. `family_spec_common.py` owns shared primitives; `family_01_*` through `family_10_*` follow first standalone evaluation order. The catalog remains the human-readable authority for backlog, modifier, meta, position-management, and option-expression families that are not yet promoted into executable Layer 3 specs.

Standalone evaluation, elimination, and promotion decisions are made at `3_strategy_family` granularity. Layer 3 intentionally does not carry a separate strategy-group field.

## Boundary

Layer 3 evaluates **single anonymous target candidates** and emits strategy setup fit. It does not choose final trade instructions.

Layer 3 may output:

- strategy family/variant;
- direction and horizon preference;
- setup-fit score and rank;
- eligibility state and reason codes;
- parameter-neighborhood stability and robustness evidence.

Layer 3 must not output:

- exact entry/exit order instructions;
- option DTE, strike, delta, premium, IV/Greeks, or contract ID;
- position size, portfolio weight, two-leg hedge ratio, or execution policy.

## Catalog summary

| Family | Basic idea | Best-fit trading periods | Variant count | Alpaca data support |
|---|---|---|---:|---|
| `moving_average_crossover` | Follow trend changes when a faster moving average crosses a slower one. | Unified 1-minute bars; sparse MA profiles cover micro through long day-level horizons; market/sector context affects strategy selection outside the family. | 864 | `equity_bar` |
| `donchian_channel_breakout` | Follow price when it breaks a prior high/low channel. | Unified 1-minute bars; channel profiles encode duration. | 144 | `equity_bar` |
| `macd_trend` | Use MACD line/signal/histogram behavior to detect trend acceleration or reversal. | Unified 1-minute bars; MACD profiles encode duration. | 288 | `equity_bar` |
| `bollinger_band_reversion` | Fade stretched prices back toward a volatility band center when context supports reversion. | Unified 1-minute bars; band profiles encode duration. | 384 | `equity_bar` |
| `rsi_reversion` | Fade overbought/oversold momentum extremes, optionally requiring divergence or higher-duration confirmation. | Unified 1-minute bars; RSI profiles encode duration. | 192 | `equity_bar` |
| `bias_reversion` | Fade large deviations from a moving average or z-score baseline. | Unified 1-minute bars; MA profiles encode duration. | 384 | `equity_bar` |
| `vwap_reversion` | Fade intraday price deviations back toward regular-session VWAP. | Unified 1-minute bars. | 108 | `equity_bar`; preferred `equity_liquidity_bar` |
| `range_breakout` | Trade a confirmed escape from a recent consolidation range. | Unified 1-minute bars; range profiles encode duration. | 288 | `equity_bar`; optional `equity_liquidity_bar` |
| `opening_range_breakout` | Trade a regular-session break above/below the opening range. | Unified 1-minute bars; opening range duration remains a variant axis. | 48 | `equity_bar`; optional `equity_liquidity_bar` |
| `volatility_breakout` | Trade when volatility expands enough to suggest a new directional move. | Unified 1-minute bars; volatility profiles encode duration. | 96 | `equity_bar`; optional `equity_liquidity_bar` |

Moved out of Layer 3 standalone implementation:

- `cross_sectional_momentum` — belongs with position/portfolio management because it ranks a universe and controls rebalance/turnover.
- `pairs_statistical_arbitrage` — belongs with position/portfolio management because it owns pair construction, hedge ratio, two-leg sizing, and spread risk.

Deferred final goals:

- `supervised_direction_classifier` — keep as the eventual supervised ML direction model after deterministic labels/baselines mature.
- `reinforcement_learning_policy` — keep as the eventual policy-learning target after simulator/reward/action validation matures.

## Variant counting rules

- `variant_count` is the product of listed variable axes unless a curated tuple axis is explicitly named.
- Fixed/default fields do not multiply variants.
- There is no fixed per-family variant ceiling. A family may define a large reviewed searchable universe, but training and promotion do not have to consume every variant.
- Variant IDs should be generated from a canonical JSON spec and stable hash.
- Grids should start sparse enough to be reviewable, then expand only when evidence shows likely value between existing gradient options.
- Variant pruning should remove variants with no observed conditional edge, not merely variants with weak aggregate monthly return.

## Standalone strategy families

### `moving_average_crossover`

Basic introduction: trend-following baseline. A bullish setup appears when a fast moving average crosses above a slow moving average; bearish is the inverse. It is simple, interpretable, and useful as a benchmark for more complex trend families.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Longer-horizon behavior is expressed by longer MA windows, not by switching model timeframe.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `exit_rule` | `opposite_cross_or_score_decay` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `ma_window_profile` | `micro_3_10`, `scalp_5_20`, `fast_10_30`, `intraday_30_120`, `intraday_90_360`, `intraday_240_960`, `equity_day_390_1950`, `continuous_day_1440_7200` | 8 |
| `price_field` | `bar_close`, `bar_hlc3` | 2 |
| `ma_type` | `ema`, `sma` | 2 |
| `crossover_confirmation_bars` | `1`, `2`, `3` | 3 |
| `cooldown_bars` | `1`, `3`, `5` | 3 |
| `min_slope` | `0.01`, `0.03`, `0.05` | 3 |
Variant count: `8 * 2 * 2 * 3 * 3 * 3 = 864`.

Reviewed searchable universe: `moving_average_crossover` currently uses an 864-variant reviewed universe so the first MA baseline can test price source, cooldown, and slope sensitivity across the accepted sparse window grid. This is not a requirement that every variant be used for model training after monthly review.

Implementation notes:

- Each `ma_window_profile` value expands to `(profile_id, fast_window_1min_bars, slow_window_1min_bars)`.
- Enforce `fast_window_1min_bars < slow_window_1min_bars` through curated `ma_window_profile` values.
- Fast profiles cover crypto and near-zero-slippage high-volume options; intraday profiles are intentionally limited to three sparse left/middle/right points; the longest initial profile preserves a long day-level right endpoint so later reviews can insert intermediate windows between accepted endpoints.
- The profile grid is intentionally sparse; add intermediate windows only when monthly evaluation shows stable uncovered performance between adjacent profiles.
- `bar_hlc3` means `(bar_high + bar_low + bar_close) / 3`.
- This family should remain a simple crossover baseline, not the final strategy selector by itself.
- Do not add an embedded trend-filter axis to this family; market and sector context should influence Layer 3 family/variant selection or weighting outside the strategy's own signal rule.

### `donchian_channel_breakout`

Basic introduction: trend/breakout family based on prior high/low channels. It attempts to catch persistent moves after price exits a historical range.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Channel, exit, and ATR durations are encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `breakout_side` | `both` |
| `retest_allowed` | `false` initially |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `channel_window_profile` | `micro_10_5_atr10`, `scalp_20_10_atr14`, `fast_30_15_atr20`, `intraday_60_30_atr30`, `intraday_120_60_atr60`, `intraday_240_120_atr120`, `equity_day_390_195_atr195`, `continuous_day_1440_720_atr720` | 8 |
| `breakout_buffer_atr` | `0`, `0.25`, `0.5` | 3 |
| `confirmation_bars` | `1`, `2` | 2 |
| `stop_atr_multiple` | `1.5`, `2.5`, `3.5` | 3 |

Variant count: `8 * 3 * 2 * 3 = 144`.

Implementation notes:

- Each `channel_window_profile` expands to `(profile_id, entry_channel_1min_bars, exit_channel_1min_bars, atr_window_1min_bars)`.
- `stop_atr_multiple` is setup/invalidation context only; actual order stops belong downstream.

### `macd_trend`

Basic introduction: trend-following and momentum-confirmation family using MACD line, signal line, and histogram behavior.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- MACD durations are encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `price_field` | `bar_close` |
| `trend_filter_window` | inherited from variant context if enabled later |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `macd_profile` | `micro_3_10_3`, `scalp_5_20_5`, `fast_8_21_5`, `intraday_12_26_9`, `intraday_24_52_18`, `intraday_60_180_45`, `intraday_120_360_90`, `intraday_240_720_180`, `equity_day_390_1014_351`, `equity_swing_1950_5070_1755`, `continuous_day_1440_3744_1296`, `continuous_swing_7200_18720_6480` | 12 |
| `histogram_threshold` | `0`, `0.25_atr_normalized` | 2 |
| `zero_line_filter` | `false`, `true` | 2 |
| `slope_confirmation_bars` | `1`, `2`, `3` | 3 |
| `exit_on_signal_cross` | `false`, `true` | 2 |

Variant count: `12 * 2 * 2 * 3 * 2 = 288`.

Implementation notes:

- Each `macd_profile` expands to `(profile_id, fast_ema_1min_bars, slow_ema_1min_bars, signal_ema_1min_bars)`.
- Normalize histogram thresholds where possible so symbols with different price scales are comparable.

### `bollinger_band_reversion`

Basic introduction: mean-reversion family. It looks for price stretched toward/outside a volatility band and scores whether return toward the center is plausible.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Band duration is encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `price_field` | `bar_close` |
| `rsi_filter_period` | optional diagnostic only initially |
| `volatility_regime_filter` | `allowed_unless_extreme_trend` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `band_window_profile` | `micro_10`, `scalp_20`, `fast_30`, `intraday_60`, `intraday_120`, `intraday_240`, `equity_day_390`, `continuous_day_1440` | 8 |
| `band_stddev` | `1.5`, `2.0`, `2.5` | 3 |
| `entry_band` | `outer_touch`, `close_outside` | 2 |
| `exit_band` | `midline`, `half_sigma` | 2 |
| `trend_filter_enabled` | `false`, `true` | 2 |
| `max_hold_minutes` | `30`, `120` | 2 |

Variant count: `8 * 3 * 2 * 2 * 2 * 2 = 384`.

Implementation notes:

- Each `band_window_profile` expands to `(profile_id, window_1min_bars)`.
- Trend filter is important: this family should avoid fading strong one-way trend regimes without extra evidence.
- `max_hold_minutes` is an evaluation/setup expiry concept, not an execution instruction.

### `rsi_reversion`

Basic introduction: mean-reversion family based on overbought/oversold momentum. It can optionally require divergence or multi-duration confirmation.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- RSI duration is encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `price_field` | `bar_close` |
| `max_hold_minutes` | family default by profile |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `rsi_period_profile` | `micro_5`, `fast_7`, `scalp_14`, `intraday_30`, `intraday_60`, `intraday_120`, `equity_day_390`, `continuous_day_1440` | 8 |
| `threshold_pair` | `(30,70)`, `(25,75)`, `(20,80)` | 3 |
| `exit_midline` | `45_55_band`, `50_cross` | 2 |
| `divergence_required` | `false`, `true` | 2 |
| `multi_duration_confirm` | `false`, `true` | 2 |

Variant count: `8 * 3 * 2 * 2 * 2 = 192`.

Implementation notes:

- Each `rsi_period_profile` expands to `(profile_id, rsi_period_1min_bars)`.
- `threshold_pair` expands to `oversold_threshold` and `overbought_threshold`.
- Divergence detection must be deterministic and point-in-time; avoid post-hoc swing-point leakage.

### `bias_reversion`

Basic introduction: mean-reversion family based on distance from a moving average or z-score baseline. It is a direct measure of price stretch.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Baseline duration is encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `price_field` | `bar_close` |
| `max_hold_minutes` | family default by profile |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `ma_window_profile` | `micro_10`, `scalp_20`, `fast_30`, `intraday_60`, `intraday_120`, `intraday_240`, `equity_day_390`, `continuous_day_1440` | 8 |
| `ma_type` | `sma`, `ema` | 2 |
| `deviation_measure` | `pct_from_ma`, `zscore_from_ma` | 2 |
| `entry_deviation_threshold` | `1.5`, `2.0`, `2.5` | 3 |
| `exit_deviation_threshold` | `0.25`, `0.5` | 2 |
| `trend_filter_enabled` | `false`, `true` | 2 |

Variant count: `8 * 2 * 2 * 3 * 2 * 2 = 384`.

Implementation notes:

- Each `ma_window_profile` expands to `(profile_id, ma_window_1min_bars)`.
- If `deviation_measure = pct_from_ma`, thresholds should be interpreted as percent/bps families; if z-score, thresholds are standard-deviation units.
- Keep threshold semantics explicit in the variant payload.

### `vwap_reversion`

Basic introduction: intraday mean-reversion family. It looks for a liquid underlying moving too far from regular-session VWAP and scores whether reversion is plausible before the option trade window decays.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat signal timeframe as a variant axis; every variant runs on the same 1-minute evidence grid.
- VWAP remains regular-session anchored.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `vwap_scope` | `regular_session_vwap` |
| `premarket_context_mode` | `context_filter` |
| `earliest_entry_time` | `10:00 ET` |
| `no_trade_after_time` | `15:30 ET` |
| `minimum_dollar_volume` | `target_relative_liquidity_gate` |
| `time_of_day_bucket` | derived label, not a variant axis |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `deviation_bps` | `30`, `50`, `75`, `100` | 4 |
| `entry_zscore` | `1.0`, `1.5`, `2.0` | 3 |
| `exit_zscore` | `0.25`, `0.5`, `0.75` | 3 |
| `maximum_spread_bps` | `5`, `10`, `15` | 3 |

Variant count: `4 * 3 * 3 * 3 = 108`.

Implementation notes:

- `minimum_dollar_volume` must be target-relative, e.g. current-window dollar volume versus rolling median/percentile for the same target.
- `time_of_day_bucket` is derived from `available_time` for diagnostics and calibration; do not let it multiply variants initially.
- Option chain and contract liquidity checks belong to `OptionExpressionModel`.

### `range_breakout`

Basic introduction: breakout family that looks for price escaping a recent consolidation range with enough confirmation to avoid wick-only false breaks.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Range duration is encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `breakout_direction` | `both` |
| `close_confirmation` | `true` |
| `failed_breakout_timeout_minutes` | family default by profile |
| `cooldown_bars` | `1` |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `range_window_profile` | `micro_10`, `scalp_20`, `fast_30`, `intraday_60`, `intraday_120`, `intraday_240`, `equity_day_390`, `continuous_day_1440` | 8 |
| `range_width_max_atr` | `1.0`, `1.5`, `2.0` | 3 |
| `breakout_buffer_atr` | `0`, `0.25`, `0.5` | 3 |
| `volume_confirmation_ratio` | `1.0`, `1.5` | 2 |
| `retest_rule` | `none`, `allow_once` | 2 |

Variant count: `8 * 3 * 3 * 2 * 2 = 288`.

Implementation notes:

- Each `range_window_profile` expands to `(profile_id, range_lookback_1min_bars)`.
- Range width cap prevents labeling already-expanded moves as range breaks.
- `retest_rule` should remain setup evidence, not a downstream order instruction.

### `opening_range_breakout`

Basic introduction: morning intraday breakout family. It defines the regular-session opening range and scores a confirmed move above or below it.

Signal bar policy:

- Use completed 1-minute bars only.
- The opening range duration remains a variant axis, but bar interval is fixed.
- Premarket can filter context but must not define the opening range.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
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

- One signal per target/session is the starting rule; repeated breakouts usually imply chop and are costly for option trades.

### `volatility_breakout`

Basic introduction: breakout/volatility family. It scores whether volatility expansion is large enough to suggest a tradable move, then uses a direction filter to avoid directionless noise.

Signal bar policy:

- Use completed 1-minute bars only.
- Do not treat bar interval as a variant axis; every variant runs on the same 1-minute evidence grid.
- Volatility duration is encoded by curated profiles.

Fixed parameters:

| Parameter | Value |
|---|---|
| `signal_bar_interval` | `1Min` |
| `cooldown_bars` | `1` |
| `volatility_cooloff_threshold` | family default by profile |

Variable gradients:

| Axis | Values | Count |
|---|---|---:|
| `volatility_profile` | `micro_atr10_x1.25`, `scalp_atr14_x1.5`, `fast_atr20_x1.5`, `intraday_atr60_x1.5`, `intraday_atr120_x2.0`, `intraday_hv240_x1.5`, `equity_day_atr390_x1.5`, `continuous_day_hv1440_x2.0` | 8 |
| `direction_filter` | `none`, `trend`, `range_break` | 3 |
| `confirmation_bars` | `1`, `2` | 2 |
| `stop_atr_multiple` | `1.5`, `2.5` | 2 |

Variant count: `8 * 3 * 2 * 2 = 96`.

Implementation notes:

- Each `volatility_profile` expands to `(profile_id, volatility_measure, volatility_window_1min_bars, expansion_threshold)`.
- A volatility breakout without direction filter should be evaluated cautiously; expansion alone does not guarantee directional edge.

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

Basic introduction: reusable filter/modifier that permits mean reversion only under acceptable higher-duration trend and pullback conditions.

Suitable periods: same as the mean-reversion family it modifies; higher-duration context should be derived from reviewed 1-minute windows rather than a separate signal timeframe.

Potential gradients:

| Axis | Values |
|---|---|
| `higher_duration_profile` | reviewed 1-minute trend-context windows |
| `higher_duration_trend_window` | `20`, `50` profile units |
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
7. **Standalone family evaluation** — test each family/variant independently before applying modifiers, meta-scoring, or ensemble selection.
8. **Pruning policy** — eliminate, downgrade, or quarantine families that fail baseline, cost, stability, or option-expression feasibility gates.
9. **Baseline comparison** — family-specific baseline and market/sector/candidate-only baseline.
10. **Stability gates** — split/refit stability, parameter-neighborhood stability, and variant-family robustness.
11. **Anonymity checks** — ensure strategy variants consume anonymous target features and reviewed context, not raw ticker/company identity.
12. **Promotion path** — no family becomes production-active until real-data evaluation and promotion review are accepted.

## Backlog family variant catalog

The catalog is not limited to the first implementation batch. Every retained strategy family should be represented here with enough parameter structure to become variants later. `implementation_status` controls rollout; it does not excuse missing variant design.

Statuses:

- `active_catalog`: ready for first implementation/evaluation batches.
- `layer3_backlog`: retained as future standalone Layer 3 family.
- `modifier`: reusable filter/score adjustment, not standalone by default.
- `meta_family`: composition or ensemble layer over other families.
- `position_management`: retained for portfolio/position layer, not Layer 3 standalone.
- `option_expression`: retained for `OptionExpressionModel`, not Layer 3.
- `event_overlay`: retained for event/overlay layer, not Layer 3 standalone.
- `deferred_ml_rl`: retained final-goal ML/RL family.
- `removed`: explicitly excluded; no variants assigned.

### Layer 3 backlog families with variant-ready axes

Backlog promotion rule: every Layer 3 backlog family must use completed 1-minute bars for signal output. Historical `timeframe` or `signal_timeframe` axes are not accepted promotion surfaces; they must be converted to curated 1-minute duration/window profiles before implementation. Provisional counts below are retained as sizing hints until each backlog row receives a full profile review.

| Family | Status | Basic idea | Suitable periods | Variable gradients | Variant count |
|---|---|---|---|---|---:|
| `adx_trend_strength` | `layer3_backlog` | Score directional trend strength with ADX/DMI. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `adx_window=14/20`; `adx_min=20/25/30`; `di_confirmation=required/optional`; `slope_confirm=0/1` | 72 |
| `parabolic_sar_trend` | `layer3_backlog` | Follow PSAR trend flips and persistence. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `sar_step=0.01/0.02/0.03`; `sar_max=0.1/0.2`; `confirmation_bars=1/2/3`; `trend_filter=off/on` | 108 |
| `supertrend_following` | `layer3_backlog` | ATR-band trend state and flips. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `atr_window=10/14/20`; `multiplier=2/3/4`; `confirmation_bars=1/2`; `direction_mode=bullish/bearish/both` | 216 |
| `ichimoku_trend` | `layer3_backlog` | Cloud and tenkan/kijun trend confirmation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `ichimoku_spec=9_26_52/12_24_48`; `cloud_filter=price_above_below/price_and_cloud_slope`; `tk_cross=required/optional`; `lagging_confirm=off/on` | 32 |
| `ma_stack_alignment` | `layer3_backlog` | Trend alignment from ordered moving-average stack. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `stack_spec=5_10_20/10_20_50/20_50_200`; `ma_type=sma/ema`; `min_separation_bps=0/10/25`; `slope_confirm=off/on` | 108 |
| `higher_high_higher_low_trend` | `layer3_backlog` | Mechanical swing-structure continuation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `swing_window=3/5/8`; `structure_count=2/3`; `break_buffer_atr=0/0.25`; `confirmation_bars=1/2` | 72 |
| `pullback_to_ma_continuation` | `layer3_backlog` | Continue trend after pullback to MA support/resistance. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `ma_window=20/50`; `ma_type=sma/ema`; `pullback_depth_atr=0.5/1.0/1.5`; `resume_confirm=close_reclaim/momentum_bar` | 96 |
| `relative_strength_vs_benchmark` | `layer3_backlog` | Single target relative strength versus benchmark/sector reference. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `benchmark_ref=market/sector`; `lookback=10/20/60`; `rs_threshold=0/0.5/1.0_z`; `confirm_bars=1/2` | 108 |
| `trend_day_continuation` | `layer3_backlog` | Intraday trend-day continuation after strong directional morning. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `morning_window=30/60`; `trend_strength_min=1.0/1.5/2.0_atr`; `pullback_allowed=none/shallow`; `no_trade_after=13:00/14:00` | 108 |
| `anchored_vwap_trend_continuation` | `layer3_backlog` | Continue trend around anchored VWAP from a reviewed anchor. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `anchor=session_open/day_high_low/gap_open`; `distance_filter_bps=0/25/50`; `reclaim_confirm=1/2`; `liquidity_filter=standard/strict` | 108 |
| `keltner_channel_reversion` | `layer3_backlog` | Revert from ATR channel extremes. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `ema_window=20/30`; `atr_window=10/20`; `multiplier=1.5/2/2.5`; `exit_rule=midline/half_channel`; `trend_filter=off/on` | 192 |
| `cci_reversion` | `layer3_backlog` | Fade CCI overextension. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `cci_window=14/20/30`; `entry_threshold=100/150/200`; `exit_threshold=0/50`; `trend_filter=off/on` | 144 |
| `stochastic_reversion` | `layer3_backlog` | Fade stochastic overbought/oversold. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `k_window=14/21`; `d_window=3/5`; `threshold_pair=20_80/10_90`; `cross_required=false/true`; `trend_filter=off/on` | 128 |
| `williams_r_reversion` | `layer3_backlog` | Fade Williams %R extremes. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `window=14/21/28`; `threshold_pair=-80_-20/-90_-10`; `exit_level=-50/-40_60_band`; `trend_filter=off/on` | 96 |
| `zscore_return_reversion` | `layer3_backlog` | Fade statistically unusual recent returns. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `return_window=3/5/10`; `zscore_window=20/60`; `entry_z=1.5/2/2.5`; `exit_z=0/0.5`; `trend_filter=off/on` | 288 |
| `gap_fade` | `layer3_backlog` | Fade opening gap after regular-session confirmation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `gap_min_bps=50/100/200`; `confirmation_minutes=15/30`; `fade_target=half_gap/full_gap`; `trend_filter=off/on` | 72 |
| `failed_breakout_reversion` | `layer3_backlog` | Fade breakout that fails back inside range. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `range_lookback=20/40`; `failure_window=3/5`; `reentry_depth=inside_close/mid_range`; `volume_filter=off/on`; `max_hold=10/20` | 96 |
| `vwap_band_reversion` | `layer3_backlog` | Fade from VWAP bands rather than raw VWAP distance. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `band_method=stddev/atr`; `band_width=1/1.5/2`; `entry_band=outer_touch/close_outside`; `exit_band=vwap/half_band`; `spread_filter=standard/strict` | 216 |
| `support_resistance_reversion` | `layer3_backlog` | Revert at mechanical support/resistance zones. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `level_method=pivot/rolling_high_low/volume_node_proxy`; `lookback=20/60`; `touch_tolerance_bps=10/25/50`; `rejection_confirm=wick/close`; `trend_filter=off/on` | 288 |
| `overnight_gap_reversion` | `layer3_backlog` | Fade overnight gap after open stabilization. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `gap_min_bps=50/100/200`; `earliest_entry=09:45/10:00`; `confirmation=first_pullback/vwap_reclaim`; `no_trade_after=11:00/12:00` | 48 |
| `keltner_channel_breakout` | `layer3_backlog` | Break out beyond ATR channel. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `ema_window=20/30`; `atr_window=10/20`; `multiplier=1.5/2/2.5`; `confirmation_bars=1/2`; `volume_filter=off/on` | 192 |
| `bollinger_band_breakout` | `layer3_backlog` | Continue volatility-band expansion. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `window=20/30`; `band_stddev=2/2.5`; `close_outside_bars=1/2`; `squeeze_required=off/on`; `volume_filter=off/on` | 128 |
| `squeeze_breakout` | `layer3_backlog` | Trade release from volatility compression. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `squeeze_method=bb_keltner/percentile_range`; `compression_window=20/60`; `release_threshold=1.0/1.5`; `direction_filter=trend/range_break`; `confirmation_bars=1/2` | 128 |
| `nr7_breakout` | `layer3_backlog` | Breakout after narrowest range in seven bars. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `narrow_range_n=4/7`; `breakout_buffer_atr=0/0.25/0.5`; `direction_mode=both`; `confirmation_bars=1/2`; `volume_filter=off/on` | 96 |
| `inside_bar_breakout` | `layer3_backlog` | Breakout from inside-bar compression. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `inside_count=1/2/3`; `breakout_buffer_bps=5/10/20`; `confirmation_bars=1/2`; `volume_filter=off/on` | 144 |
| `gap_continuation` | `layer3_backlog` | Continue strong gap after confirmation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `gap_min_bps=50/100/200`; `hold_above_open_minutes=15/30`; `volume_confirmation=1/1.5`; `direction_mode=both` | 54 |
| `high_low_range_expansion` | `layer3_backlog` | Trade expansion of high-low range versus baseline. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `baseline_window=20/60`; `expansion_ratio=1.25/1.5/2`; `direction_filter=none/trend`; `confirmation_bars=1/2` | 96 |
| `volume_price_breakout` | `layer3_backlog` | Price breakout confirmed by relative volume. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `price_break_lookback=20/40`; `volume_ratio=1.25/1.5/2`; `breakout_buffer_bps=5/10/20`; `confirmation_bars=1/2` | 144 |
| `atr_trailing_breakout` | `layer3_backlog` | Directional break with ATR trailing invalidation context. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `atr_window=14/20`; `trail_multiple=2/3/4`; `break_confirm=1/2`; `direction_filter=trend/range_break` | 96 |
| `opening_drive_continuation` | `layer3_backlog` | Continue a strong first 30-60m opening drive. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `drive_window=30/60`; `drive_atr_min=1/1.5/2`; `pullback_rule=none/shallow`; `no_trade_after=11:00/12:00` | 108 |
| `relative_volume_surge_continuation` | `layer3_backlog` | Continue moves with abnormal relative volume. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `rv_window=20/60`; `rv_ratio=1.5/2/3`; `price_confirm=close_up_down/breakout`; `spread_filter=standard/strict` | 96 |
| `volume_climax_reversal` | `layer3_backlog` | Fade exhaustion after volume climax. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `volume_ratio=2/3/5`; `range_extension_atr=1/1.5/2`; `reversal_confirm=wick/close`; `trend_filter=off/on` | 144 |
| `spread_compression_breakout` | `layer3_backlog` | Breakout after spread/liquidity improves. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `compression_window=10/20/30`; `spread_percentile=20/30`; `breakout_buffer_bps=5/10/20`; `volume_filter=off/on` | 108 |
| `trade_count_activity_surge` | `layer3_backlog` | Activity burst as continuation confirmation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `activity_window=10/20/60`; `trade_count_ratio=1.5/2/3`; `price_confirm=trend/breakout`; `spread_filter=standard/strict` | 108 |
| `vwap_minus_mid_dislocation` | `layer3_backlog` | Score dislocation between trade VWAP and quote mid. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `dislocation_bps=5/10/20`; `persistence_bars=1/2/3`; `direction_mode=mean_revert/continue`; `spread_filter=strict` | 36 |
| `quote_imbalance_pressure` | `layer3_backlog` | Use bid/ask size imbalance as directional pressure. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `imbalance_threshold=0.6/0.7/0.8`; `persistence_bars=1/2/3`; `price_confirm=off/on`; `spread_filter=strict` | 36 |
| `liquidity_vacuum_breakout` | `layer3_backlog` | Breakout when liquidity thins and price moves. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `spread_widening_bps=5/10/20`; `depth_proxy_drop=20/40`; `price_break=5/10/20_bps`; `risk_filter=strict` | 54 |
| `midday_range_breakout` | `layer3_backlog` | Breakout from lunchtime consolidation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `range_window=60/90/120`; `breakout_buffer_bps=5/10/20`; `volume_ratio=1/1.5`; `no_trade_after=14:00/14:30` | 108 |
| `afternoon_trend_continuation` | `layer3_backlog` | Continue established afternoon trend before cutoff. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `trend_window=30/60/120`; `pullback_depth=0.5/1.0_atr`; `no_trade_after=15:00/15:30`; `liquidity_filter=standard/strict` | 72 |
| `power_hour_breakout` | `layer3_backlog` | Late-day breakout/continuation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `range_window=30/60`; `breakout_buffer_bps=5/10/20`; `volume_ratio=1.5/2`; `risk_mode=strict_only` | 36 |
| `morning_reversal` | `layer3_backlog` | Fade first-hour extreme after confirmation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `extreme_window=30/60`; `extension_atr=1/1.5/2`; `confirm=vwap_reclaim/range_reentry`; `no_trade_after=11:00/12:00` | 108 |
| `lunch_reversion` | `layer3_backlog` | Revert midday overextension. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `window=60/90/120`; `zscore=1.5/2/2.5`; `target=vwap/mid_range`; `spread_filter=standard/strict` | 72 |
| `previous_day_high_low_break` | `layer3_backlog` | Break prior day high/low. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `level=prev_high/prev_low/both`; `buffer_bps=5/10/20`; `confirmation_bars=1/2`; `volume_filter=off/on` | 96 |
| `previous_close_gap_hold` | `layer3_backlog` | Gap holds beyond previous close and continues. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `gap_min_bps=50/100/200`; `hold_minutes=15/30/60`; `direction_mode=both`; `volume_filter=off/on` | 54 |
| `first_pullback_after_opening_drive` | `layer3_backlog` | Continue after first pullback in trend day. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `drive_window=30/60`; `pullback_depth_atr=0.5/1/1.5`; `resume_confirm=break_pullback_high/vwap_hold`; `no_trade_after=12:00/13:00` | 72 |
| `engulfing_reversal` | `layer3_backlog` | Mechanical engulfing candle reversal. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `body_ratio_min=1/1.5/2`; `trend_context=required/optional`; `volume_filter=off/on`; `confirmation_bars=1/2` | 96 |
| `pin_bar_reversal` | `layer3_backlog` | Wick rejection reversal. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `wick_body_ratio=2/3/4`; `location=band/level/any`; `confirmation_bars=1/2`; `trend_filter=off/on` | 144 |
| `inside_outside_bar_pattern` | `layer3_backlog` | Inside/outside bar continuation or reversal. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `pattern=inside/outside`; `mode=continuation/reversal`; `confirmation_bars=1/2`; `volume_filter=off/on` | 64 |
| `three_bar_reversal` | `layer3_backlog` | Three-bar exhaustion/reversal. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `extension_atr=1/1.5/2`; `middle_bar_rule=required/optional`; `confirmation=close_reversal/range_break`; `volume_filter=off/on` | 96 |
| `breakaway_gap_pattern` | `layer3_backlog` | Gap plus follow-through continuation. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `gap_min_bps=100/200/300`; `followthrough_minutes=15/30/60`; `volume_ratio=1/1.5/2`; `direction_mode=both` | 81 |
| `measured_move_continuation` | `layer3_backlog` | Follow proportional continuation after first leg. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `leg_window=10/20/40`; `projection_ratio=0.5/1.0/1.5`; `pullback_depth=0.382/0.5/0.618`; `confirm=break/reclaim` | 162 |
| `support_resistance_break_retest` | `layer3_backlog` | Break and retest of mechanical level. | Unified 1-minute bars; profile pending review. | `signal_bar_interval=1Min`; `duration_profile=reviewed_1min_window_grid`; `level_method=pivot/rolling_high_low`; `lookback=20/60`; `retest_tolerance_bps=10/25/50`; `confirmation=wick/close`; `volume_filter=off/on` | 192 |

### Position / portfolio-management variant families

These are retained with variants, but their implementation owner is not Layer 3 standalone strategy selection.

| Family | Status | Basic idea | Suitable periods | Variable gradients | Variant count |
|---|---|---|---|---|---:|
| `cross_sectional_momentum` | `position_management` | Rank a universe by momentum and allocate/choose winners or losers. | Daily, weekly; intraday only after universe/liquidity maturity. | `ranking_lookback=20/60/120`; `skip_window=0/5/20`; `selection_quantile=10/20/30`; `rebalance_horizon=1D/5D/20D`; `vol_adjust=off/on`; `sector_neutral=off/on` | 324 |
| `pairs_statistical_arbitrage` | `position_management` | Two-leg spread reversion. | Daily, hourly research; intraday only for highly liquid pairs. | `lookback_window=60/120/252`; `spread_model=price_ratio/log_spread/residual`; `hedge_ratio=static/rolling_ols`; `entry_z=1.5/2/2.5`; `exit_z=0/0.5`; `stop_z=3/4`; `correlation_min=0.7/0.85` | 648* |
| `sector_rotation_allocation` | `position_management` | Allocate among sectors based on rotation evidence. | Daily, weekly. | `lookback=20/60/120`; `rank_method=return/vol_adj/sector_context`; `top_n=1/3/5`; `rebalance=weekly/monthly`; `risk_cap=standard/strict` | 162 |
| `risk_parity_allocation` | `position_management` | Allocate by risk contribution. | Daily, weekly. | `vol_window=20/60/120`; `covariance=diagonal/shrinkage`; `rebalance=weekly/monthly`; `max_weight=20/30/50`; `vol_target=low/medium/high` | 162 |
| `volatility_targeting_overlay` | `position_management` | Adjust exposure by realized volatility. | Daily, weekly. | `vol_window=20/60`; `target_vol=10/15/20`; `scaling_speed=slow/medium/fast`; `cap=1x/1.5x`; `floor=0/0.25x` | 72 |
| `anti_martingale_sizing_overlay` | `position_management` | Increase exposure after gains under controls. | Daily/intraday after risk layer. | `win_window=3/5/10`; `scale_step=0.25/0.5`; `max_scale=1.5/2`; `reset_rule=loss/drawdown/time`; `risk_gate=standard/strict` | 72 |

`pairs_statistical_arbitrage` is a large searchable universe if fully expanded. It must use reviewed combinations or sampled grids before implementation and belongs outside Layer 3 standalone strategy selection.

### OptionExpressionModel variant families

These are retained with variant shape but belong to option expression, not Layer 3.

| Family | Status | Basic idea | Suitable periods | Variable gradients | Variant count |
|---|---|---|---|---|---:|
| `long_call_expression` | `option_expression` | Express bullish setup as long call. | Intraday, swing 1-5D, swing 5-20D. | `dte_bucket=0DTE/1_5D/7_21D/30_60D`; `delta_bucket=0.25/0.35/0.5/0.65`; `max_spread_bps=5/10/15`; `iv_filter=none/avoid_high`; `premium_budget=low/medium/high` | 192 |
| `long_put_expression` | `option_expression` | Express bearish setup as long put. | Intraday, swing 1-5D, swing 5-20D. | `dte_bucket=0DTE/1_5D/7_21D/30_60D`; `delta_bucket=0.25/0.35/0.5/0.65`; `max_spread_bps=5/10/15`; `iv_filter=none/avoid_high`; `premium_budget=low/medium/high` | 192 |
| `debit_spread_expression` | `option_expression` | Express setup with capped-risk vertical spread. | Swing 1-5D, swing 5-20D. | `dte_bucket=7_21D/30_60D`; `long_delta=0.35/0.5`; `short_delta=0.15/0.25`; `width=standard/wide`; `iv_filter=avoid_high/any` | 32 |
| `iv_rank_filter` | `option_expression` | Gate option entry by IV context. | All option periods. | `iv_rank_max=50/70/90`; `iv_percentile_max=50/70/90`; `mode=gate/score`; `lookback=60/252` | 36 |
| `delta_bucket_selection` | `option_expression` | Choose contract delta/moneyness. | All option periods. | `direction=bullish/bearish`; `delta_bucket=0.25/0.35/0.5/0.65`; `liquidity_mode=standard/strict`; `moneyness=otm/atm/itm` | 48 |
| `dte_bucket_selection` | `option_expression` | Choose expiration horizon. | Intraday/swing. | `horizon=intraday/swing_1_5d/swing_5_20d`; `dte_bucket=0DTE/1_5D/7_21D/30_60D`; `theta_tolerance=low/medium/high`; `liquidity_mode=standard/strict` | 72 |
| `theta_decay_filter` | `option_expression` | Avoid poor time-decay tradeoffs. | Intraday/swing. | `theta_budget=low/medium/high`; `dte_bucket=0DTE/1_5D/7_21D`; `mode=gate/score`; `iv_mode=normal/high_only` | 36 |
| `option_liquidity_filter` | `option_expression` | Gate by option spread/open interest/volume. | All option periods. | `spread_max=5/10/15`; `volume_min=low/medium/high`; `open_interest_min=low/medium/high`; `mode=standard/strict` | 54 |

### Event / overlay variant families

Event-driven standalone strategies remain removed from current Layer 3, but event/overlay variants are retained for later overlay ownership.

| Family | Status | Basic idea | Suitable periods | Variable gradients | Variant count |
|---|---|---|---|---|---:|
| `earnings_gap_reaction` | `event_overlay` | React to post-earnings gap behavior. | Intraday, 1-5D swing. | `gap_min=2/5/10_pct`; `reaction_mode=fade/continue`; `confirmation_minutes=30/60`; `iv_filter=avoid_extreme/any`; `liquidity=strict` | 36 |
| `earnings_iv_crush_avoidance` | `event_overlay` | Avoid long premium into IV crush. | Options only. | `days_to_event=0/1/3/7`; `iv_rank_min=50/70/90`; `mode=gate/score`; `exception=none/after_event_only` | 48 |
| `macro_release_volatility_filter` | `event_overlay` | Gate around CPI/FOMC/NFP. | Intraday/daily. | `event_type=CPI/FOMC/NFP`; `blackout_before=30m/60m/1d`; `blackout_after=30m/60m/1d`; `mode=gate/score` | 108 |
| `news_sentiment_reaction` | `event_overlay` | React to news sentiment/features. | Intraday, daily. | `sentiment_source=alpaca/derived`; `score_threshold=medium/high`; `reaction_mode=fade/continue`; `freshness=15m/60m/1d`; `liquidity=strict` | 48 |
| `analyst_rating_reaction` | `event_overlay` | React to upgrades/downgrades. | Intraday, daily. | `action=upgrade/downgrade/both`; `broker_tier=all/high`; `gap_filter=off/on`; `confirmation=price/volume`; `freshness=1d/3d` | 48 |
| `sec_filing_reaction` | `event_overlay` | React to 8-K/filing events. | Intraday, daily. | `filing_type=8k/10q/10k/material`; `reaction_mode=avoid/fade/continue`; `freshness=1d/3d`; `confirmation=price/volume` | 48 |
| `halt_resume_pattern` | `event_overlay` | Handle halt/resume volatility. | Intraday only. | `halt_type=volatility/news/unknown`; `resume_wait=5/15/30m`; `mode=avoid/strict_reaction`; `liquidity=strict` | 24 |

### Deferred ML/RL variant families

These are variant-shaped final goals. They should not be implemented before deterministic baselines, labels, leakage checks, and validation protocols are mature.

| Family | Status | Basic idea | Suitable periods | Variable gradients | Variant count |
|---|---|---|---|---|---:|
| `supervised_direction_classifier` | `deferred_ml_rl` | Predict future direction/return bucket. | 30Min, 1Hour, 1Day first. | `model_class=logistic/xgboost/lightgbm`; `feature_set=technical/technical_liquidity/family_outputs`; `label_horizon=1/3/5/10_bars`; `prob_threshold=0.55/0.6/0.65`; `calibration=none/isotonic` | 270 |
| `supervised_strategy_selector` | `deferred_ml_rl` | Choose best deterministic family/variant for a candidate. | After family outputs mature. | `model_class=xgboost/lightgbm`; `candidate_family_set=core/all`; `label=best_family/best_variant/take_skip`; `validation=walk_forward/purged_kfold`; `threshold=standard/strict` | 48 |
| `meta_labeling_filter` | `deferred_ml_rl` | Predict whether a deterministic signal should be taken. | Same as underlying signal. | `base_signal_set=core/trend/reversion/breakout`; `model_class=logistic/xgboost/lightgbm`; `label_horizon=1/3/5_bars`; `threshold=0.55/0.6/0.65`; `calibration=none/isotonic` | 162 |
| `probabilistic_return_forecaster` | `deferred_ml_rl` | Predict distribution/quantiles of forward return. | 30Min, 1Hour, 1Day first. | `model_class=quantile_gbm/ngboost`; `feature_set=technical/technical_liquidity/family_outputs`; `horizon=1/3/5/10_bars`; `quantile_set=3q/5q`; `calibration=none/conformal` | 96 |
| `reinforcement_learning_policy` | `deferred_ml_rl` | Learn actions in simulated environment. | Not selected yet. | `environment=single_asset/multi_asset`; `action_space=discrete/continuous`; `reward=pnl/sharpe/drawdown_penalized`; `cost_model=basic/strict`; `policy_class=dqn/ppo/sac`; `validation=offline_walk_forward/paper_trade_gate` | 144 |

### Removed families

These are intentionally not variant-expanded in this catalog unless the project boundary changes.

| Family | Status | Reason |
|---|---|---|
| `cross_exchange_arbitrage` | `removed` | Venue transfer/execution/latency problem, not current Alpaca equity/options strategy selection. |
| `cash_futures_basis_arbitrage` | `removed` | Requires futures/carry/margin/settlement stack outside current boundary. |
| `funding_rate_arbitrage` | `removed` | Crypto perpetual/funding venue stack outside current boundary. |
| `grid_trading` | `removed` | Inventory/execution/position-management behavior; unsafe as Layer 3 standalone family. |
| `martingale_anti_martingale` | `removed` | Martingale disallowed; anti-martingale only as constrained sizing overlay if ever reopened. |
| `passive_market_making` | `removed` | Order-book/inventory/latency execution system, not Layer 3 setup selection. |
| `onchain_sentiment_reaction` | `removed` | Crypto/on-chain data not current Alpaca equity/options boundary. |
