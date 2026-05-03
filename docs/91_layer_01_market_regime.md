# Layer 01 - MarketRegimeModel

This file records the current `trading-model` contract for Layer 1.

## Input

```text
trading_data.feature_01_market_regime
```

Layer 1 consumes broad-market and cross-asset evidence only. Sector/industry rotation, sector/industry ETF leadership, ETF holdings, selected securities, strategies, option contracts, portfolio actions, and future-return labels are excluded from production construction.

## Physical artifacts

```text
trading_model.model_01_market_regime
trading_model.model_01_market_regime_explainability
trading_model.model_01_market_regime_diagnostics
```

## `model_01_market_regime` - output

The primary output is the narrow, stable downstream contract. It contains identity fields plus market-context state factors that downstream layers may depend on:

```text
available_time
model_id
model_version
1_price_behavior_factor
1_trend_certainty_factor
1_capital_flow_factor
1_sentiment_factor
1_valuation_pressure_factor
1_fundamental_strength_factor
1_macro_environment_factor
1_market_structure_factor
1_risk_stress_factor
1_transition_pressure
1_data_quality_score
```

## `model_01_market_regime_explainability` - explainability

Explainability owns human-review detail that should not become a hard downstream dependency:

- factor attribution;
- source feature contributions;
- bucket-level scores;
- evidence-role references;
- config and factor-spec version references;
- reason-code detail when accepted.

## `model_01_market_regime_diagnostics` - diagnostics

Diagnostics owns acceptance, monitoring, and gating evidence:

- freshness and missingness;
- minimum-history satisfaction;
- standardization and z-score clipping checks;
- feature coverage and data-quality decomposition;
- chronological split and rolling/refit stability;
- downstream usefulness versus baselines;
- no-future-leak checks.

## Naming rule

Layer 1 model fields use compact `1_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading column names when needed rather than storing semantic aliases such as `layer01_*`.
