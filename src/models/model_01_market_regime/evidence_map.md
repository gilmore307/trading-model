# MarketRegimeModel evidence map

This file owns the reviewed evidence map for `model_01_market_regime`. It is model-local documentation for the Layer 1 construction contract; registry promotion should happen only after downstream consumers prove a name needs shared status.

## Boundary

Layer 1 maps point-in-time rows from `trading_data.feature_01_market_regime` into broad market tradability/regime state keyed by `available_time`.

It must not produce sector/industry ETF rankings, selected securities, strategy choices, option contracts, position sizes, final actions, or portfolio actions. Sector/industry interpretation starts in Layer 2.

## Evidence role vocabulary

| Role | Meaning |
|---|---|
| Primary evidence | Feature families that directly contribute to a public Layer 1 state output through an internal signal group in `config/factor_specs.toml`. |
| Diagnostic evidence | Evidence reviewed with the state output to explain, sanity-check, or dispute behavior, but not currently used in construction. |
| Quality evidence | Coverage, freshness, minimum-history, standardization, and missingness evidence used by `1_coverage_score`, `1_data_quality_score`, or acceptance review. |
| Evaluation-only evidence | Labels or downstream outcomes used only after state construction to test usefulness. |
| Intentionally unused evidence | Available evidence excluded from Layer 1 because it belongs to another layer, leaks future information, or encodes a target/candidate decision. |

## Public state outputs

```text
1_market_direction_score
1_market_direction_strength_score
1_market_trend_quality_score
1_market_stability_score
1_market_risk_stress_score
1_market_transition_risk_score
1_breadth_participation_score
1_correlation_crowding_score
1_dispersion_opportunity_score
1_market_liquidity_pressure_score
1_market_liquidity_support_score
1_coverage_score
1_data_quality_score
```

## Construction evidence

The current signal specification expands to 857 unique signal columns. The table below records the intended meaning of the construction families rather than every expanded column name.

| Public output | Primary evidence families | Direction semantics | Diagnostic evidence | Evaluation-only checks |
|---|---|---|---|---|
| `1_market_direction_score` | SPY, QQQ, IWM, DIA, and RSP short-horizon returns, distance-to-MA20, and MA20 slope. | Signed broad market direction evidence. Sign is not a trade instruction. | Cross-check against longer trend quality, breadth, and volatility stress to catch one-bar spikes. | Does direction evidence improve Layer 2 sector tradability explanation beyond sector-local features? |
| `1_market_direction_strength_score` | Absolute magnitude of the same broad price-behavior evidence used by `1_market_direction_score`. | Higher means stronger directional evidence regardless of sign. | Compare with trend quality and transition risk to avoid treating noisy one-bar movement as stable direction. | Does strength help separate clean trend windows from low-conviction movement? |
| `1_market_trend_quality_score` | SPY, QQQ, IWM, DIA, and RSP 20-day return, distance-to-MA50/MA200, MA slopes, MA alignment, and MA spread evidence. | Higher means the broad-market trend is more persistent and technically aligned. | Compare with transition risk, realized volatility, correlation spikes, and breadth deterioration. | Does trend quality condition target/sector tradability stability and reduce whipsaw/no-trade errors? |
| `1_market_stability_score` | Trend-quality evidence combined against risk/stress evidence. | Higher means market context is smoother and less stress-dominated. | Compare against transition risk and correlation/crowding to detect unstable apparent trends. | Does stability reduce false handoffs to Layer 2/3? |
| `1_market_risk_stress_score` | Cross-asset realized volatility, volatility-percentile/z-score, Parkinson/Garman-Klass volatility, and relative-volatility ratio evidence. | Higher means greater broad risk/stress intensity. | Compare against VIXY, credit, correlation, drawdown, and transition risk. | Does it improve no-trade policy, size reduction, exit urgency, and kill-switch evaluation? |
| `1_market_transition_risk_score` | Adjacent-row movement across the current public state vector. | Higher means context is changing quickly. | Compare with realized volatility, breadth breaks, and correlation/crowding changes. | Does it reduce handoff errors when broad context is switching? |
| `1_breadth_participation_score` | Broad-market participation and breadth-style proxy columns available in Feature 01. | Higher means stronger broad participation support. | Compare with concentration/crowding and sector-observation evidence kept in Layer 2. | Does breadth add explanatory value after price behavior/trend quality? |
| `1_correlation_crowding_score` | Market-wide breadth, concentration, correlation, dispersion, and fragility-style structure columns. | Higher means stronger crowding/correlation/structure pressure according to reviewed signs. | Compare against broad ETF trend, volatility, and transition risk to separate healthy participation from crowding/fragility. | Does it improve downstream stability versus using broad ETF returns alone? |
| `1_dispersion_opportunity_score` | Participation/breadth evidence combined against absolute crowding/correlation pressure. | Higher means dispersion context is cleaner and less crowding-dominated. | Compare against Layer 2 sector/industry rotation evidence without importing sector leadership into Layer 1. | Does it condition whether downstream target-state comparisons have enough cross-sectional separation? |
| `1_market_liquidity_pressure_score` | HYG/LQD behavior, duration/credit relative-strength structures, valuation/rates pressure, and risk/stress evidence. | Higher means more broad liquidity/funding/cost pressure. | Review against drawdowns, rate pressure, and provider liquidity proxies. | Does it separate risk-on/risk-off windows without becoming a direct return forecast? |
| `1_market_liquidity_support_score` | Capital-flow, sentiment/risk-appetite, and risk/stress evidence with support-oriented signs. | Higher means better broad liquidity/depth/capacity support. | Check against risk stress and transition risk to avoid treating unstable speculation as durable support. | Does it improve downstream option-expression no-trade and cost-tolerance decisions? |
| `1_coverage_score` | Signal coverage, minimum prior-history satisfaction, and row-level construction completeness. | Higher means more complete usable evidence. It is not an opportunity or risk-on signal. | Review missingness by signal family and timestamp. | Does coverage gating prevent low-evidence states from being promoted? |
| `1_data_quality_score` | Same construction coverage score for existing quality/gating consumers. | Higher means row evidence is more complete and reliable. It is not trend certainty or opportunity. | Review stale/missing/non-numeric input detection and z-score floor behavior. | Does data-quality gating prevent low-evidence states from being promoted? |

## Quality evidence

Quality evidence is not a market opinion. It supports whether the row is safe to use:

- signal coverage per output and per row;
- minimum prior-history satisfaction by signal group;
- stale/missing/non-numeric input detection;
- rolling standardization floors and z-score clipping behavior;
- feature-payload ownership checks: every Feature 01 key is either primary, diagnostic, quality, evaluation-only, or intentionally unused.

`1_coverage_score` and `1_data_quality_score` must not be used as risk-on/risk-off market signals by themselves.

## Evaluation-only evidence

The following evidence may be used after state construction but must not enter same-row construction:

- future broad-market, sector/industry, and candidate returns;
- triple-barrier or forward-horizon labels;
- downstream Layer 2 sector trend-stability improvements;
- downstream action performance and disabled-action outcomes;
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
2. every primary signal maps to one public market-context output with reviewed sign and minimum history;
3. diagnostic/evaluation-only evidence is not used in same-row construction;
4. `market_context_state` is useful as conditioning context for Layer 2/3/5/7 compared with a market-context-free baseline;
5. output behavior is stable under chronological splits and rolling/expanding refits;
6. confusing or stale names are removed from the public contract rather than preserved as aliases.
