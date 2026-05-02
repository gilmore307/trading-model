# MarketRegimeModel V1 evidence map

This file owns the reviewed evidence map for `model_01_market_regime`.
It is model-local documentation for the current Layer 1 construction contract;
registry promotion should happen only after downstream consumers prove the names need
shared status.

## Boundary

Layer 1 maps point-in-time rows from `trading_data.feature_01_market_regime`
into broad market-property factors keyed by `available_time`.

It must not produce sector/industry ETF rankings, selected securities, strategy
choices, option contracts, or portfolio actions. Sector/industry interpretation
starts in Layer 2.

## Evidence role vocabulary

| Role | Meaning in V1 |
|---|---|
| Primary evidence | Feature families that directly contribute to a factor in `config/factor_specs.toml`. |
| Diagnostic evidence | Evidence reviewed with the factor to explain, sanity-check, or dispute behavior, but not currently used in factor construction. |
| Quality evidence | Coverage, freshness, minimum-history, standardization, and missingness evidence used by `1_data_quality_score` or acceptance review. |
| Evaluation-only evidence | Labels or downstream outcomes used only after factor construction to test usefulness. |
| Intentionally unused evidence | Available evidence excluded from Layer 1 because it belongs to another layer, leaks future information, or encodes a target/candidate decision. |

## Current construction evidence

The current factor specification expands to 857 unique signal columns. The table
below records the intended meaning of the primary construction families rather
than every expanded column name.

| Factor | Primary evidence families | Direction semantics | Diagnostic evidence | Evaluation-only checks |
|---|---|---|---|---|
| `1_price_behavior_factor` | SPY, QQQ, IWM, DIA, and RSP short-horizon returns, distance-to-MA20, and MA20 slope. | Higher means stronger broad current price behavior. | Cross-check against longer trend certainty, breadth, and volatility stress to catch one-bar spikes. | Does current price behavior improve Layer 2 sector trend-stability explanation beyond sector-local features? |
| `1_trend_certainty_factor` | SPY, QQQ, IWM, DIA, and RSP 20-day return, distance-to-MA50/MA200, MA slopes, MA alignment, and MA spread evidence. | Higher means the broad-market trend is more persistent and technically aligned. | Compare with transition pressure, realized volatility, correlation spikes, and breadth deterioration. | Does trend certainty condition security/strategy selection stability and reduce whipsaw/no-trade errors? |
| `1_capital_flow_factor` | HYG/LQD level behavior, HYG/LQD/TLT relative-strength structures, and credit/duration relative-volatility evidence. | Current signs make HYG/LQD level/trend groups decrease the factor and credit-duration relative-volatility groups increase it; review treats this as a pressure/stress-oriented capital-flow context until renamed or recalibrated. | Review against market drawdowns, rate-pressure evidence, and liquidity/funding proxies. | Does it separate risk-on/risk-off windows for Layer 2/3 without becoming a direct return forecast? |
| `1_sentiment_factor` | Crypto beta ETFs, growth/small/equal-weight vs SPY, crypto relative-strength pairs, inverse VIXY behavior, and related relative-volatility evidence. | Higher means stronger broad risk appetite / speculative participation; VIXY strength lowers sentiment. | Check against price behavior, risk stress, breadth, and transition pressure to avoid treating unstable speculation as durable trend. | Does it improve option-expression no-trade/volatility tolerance and strategy-family compatibility? |
| `1_valuation_pressure_factor` | TLT/IEF behavior, duration trend evidence, long-vs-short duration ratios, and duration relative-volatility evidence. | Higher values currently represent greater valuation/discount-rate pressure after configured signs. | Compare with macro environment, capital flow, and equity multiple-sensitive behavior. | Does it help explain when otherwise strong trend evidence should receive stricter DTE/delta/risk constraints? |
| `1_fundamental_strength_factor` | Broad-market participation and breadth-style proxy columns currently available in Feature 01. | Higher means stronger broad participation proxy, not issuer-level fundamental health. | Treat as provisional until true point-in-time fundamental evidence is added; compare with breadth and concentration diagnostics. | Does it add explanatory value after price behavior/trend certainty, or should it remain a diagnostic/provisional factor? |
| `1_macro_environment_factor` | Dollar, commodity, precious-metal, energy, agriculture, copper, and cross-asset relative-strength/volatility evidence. | Higher means stronger configured macro-pressure context; it is a conditioning vector, not a macro forecast. | Review alongside risk stress, valuation pressure, and capital-flow evidence for conflicting macro regimes. | Does it improve portfolio-risk policy and option-expression constraints in commodity/dollar/rate-sensitive windows? |
| `1_market_structure_factor` | Market-wide breadth, concentration, correlation, dispersion, and fragility-style structure columns. | Higher means structure evidence is more pronounced according to configured signs; interpretation must be reviewed with supporting diagnostics. | Compare against broad ETF trend, volatility, and transition pressure to separate healthy participation from crowding/fragility. | Does it improve downstream stability versus using broad ETF returns alone? |
| `1_risk_stress_factor` | Cross-asset realized volatility, volatility-percentile/z-score, Parkinson/Garman-Klass volatility, and relative-volatility ratio evidence. | Higher means greater broad risk/stress intensity. | Compare against VIXY, credit, correlation, drawdown, and transition pressure. | Does it improve no-trade policy, size reduction, exit urgency, and kill-switch evaluation? |

## Quality evidence

Quality evidence is not a market opinion. It supports whether the row is safe to
use:

- signal coverage per factor and per row;
- minimum prior-history satisfaction by signal group;
- stale/missing/non-numeric input detection;
- rolling standardization floors and z-score clipping behavior;
- feature-payload ownership checks: every Feature 01 key is either primary,
  diagnostic, quality, evaluation-only, or intentionally unused.

`1_data_quality_score` summarizes construction coverage. It must not be used as a
risk-on/risk-off market signal by itself.

## Transition pressure

`1_transition_pressure` is a row-level instability indicator derived from changes
in the bounded market-property vector. It is not a separate regime label. It is
used to warn downstream layers that the market context may be changing quickly
and that trend/strategy/option/risk decisions should require stronger evidence.

## Evaluation-only evidence

The following evidence may be used after factor construction but must not enter
same-row factor construction:

- future broad-market, sector/industry, and candidate returns;
- triple-barrier or forward-horizon labels;
- downstream Layer 2 sector trend-stability improvements;
- strategy-family performance and disabled-strategy outcomes;
- option-expression PnL, IV/theta/vega outcome diagnostics, and no-trade results;
- portfolio drawdown, exposure, sizing, exit, and kill-switch outcomes.

## Intentionally unused evidence

The following evidence is intentionally outside Layer 1 construction:

- sector/industry rotation conclusions and ETF/sector leadership labels;
- sector/industry candidate ETF rankings;
- final stock/security selections or ticker-aware target features;
- strategy choices, entry timing, option contract selection, position size, and portfolio weights;
- future returns, realized PnL, and post-decision execution outcomes;
- provider/source metadata that belongs to `trading-data` rather than model output construction.

## Maturation checks

A Layer 1 change is not accepted merely because tests pass. Review must show:

1. every new Feature 01 key has an explicit evidence role;
2. every primary signal maps to one market-property factor with reviewed sign and minimum history;
3. diagnostic/evaluation-only evidence is not used in same-row construction;
4. `market_context_state` is useful as conditioning context for Layer 2/3/5/7 compared with a market-context-free baseline;
5. factor behavior is stable under chronological splits and rolling/expanding refits;
6. confusing or stale factor names are removed instead of preserved as compatibility aliases.
