# Layer 01 - MarketRegimeModel

This file records the current `trading-model` contract for Layer 1.

## Input

```text
trading_data.feature_01_market_regime
```

Layer 1 consumes broad-market and cross-asset evidence only. Sector/industry rotation, sector/industry ETF leadership, ETF holdings, selected securities, strategies, option contracts, portfolio actions, and future-return labels are excluded from production construction.

## Stage flow

```mermaid
flowchart LR
    source["trading_data source evidence<br/>point-in-time broad-market and cross-asset data"]
    feature["trading_data.feature_01_market_regime<br/>deterministic Layer 1 feature surface"]
    model["MarketRegimeModel<br/>Layer 1 model logic"]
    output["trading_model.model_01_market_regime<br/>primary market_context_state"]
    explain["trading_model.model_01_market_regime_explainability<br/>human-review factor attribution"]
    diagnostics["trading_model.model_01_market_regime_diagnostics<br/>acceptance and gating evidence"]
    downstream["Layer 2+ conditioning context<br/>not sector/security selection"]

    source --> feature --> model
    model --> output --> downstream
    model --> explain
    model --> diagnostics
```

## Physical artifacts

```text
trading_model.model_01_market_regime
trading_model.model_01_market_regime_explainability
trading_model.model_01_market_regime_diagnostics
```

## `model_01_market_regime` - output

The primary output is the narrow, stable downstream contract. It is keyed by `available_time` and contains market-context state factors that downstream layers may depend on:

```text
available_time
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

Explainability owns human-review detail that should not become a hard downstream dependency. The current generic SQL artifact is optional but, when written, uses one row per `(available_time, factor_name)` with:

```text
available_time
factor_name
factor_value
explanation_payload_json
```

`explanation_payload_json` owns factor attribution context such as aggregation, reducer, required coverage, reviewed signal counts, evidence-role references, config/factor-spec references, and future accepted reason-code detail.

## `model_01_market_regime_diagnostics` - diagnostics

Diagnostics owns acceptance, monitoring, and gating evidence. The current generic SQL artifact is optional but, when written, uses one row per `available_time` with:

```text
available_time
present_factor_count
missing_factor_count
data_quality_score
diagnostic_payload_json
```

`diagnostic_payload_json` owns missingness/freshness, minimum-history, standardization and z-score clipping checks, feature coverage, data-quality decomposition, chronological split/refit stability, downstream usefulness versus baselines, and no-future-leak checks.

## Naming rule

Layer 1 model fields use compact `1_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading column names when needed rather than storing semantic aliases such as `layer01_*`.

## Layer acceptance

Layer 1 changes are acceptable when they:

- preserve the broad-market-only boundary and exclude sector/security/strategy/option/portfolio outcome leakage;
- keep `trading_data.feature_01_market_regime` as the production input and `trading_model.model_01_market_regime` as the narrow downstream output;
- keep explainability and diagnostics as review/support artifacts rather than hard downstream dependencies;
- provide evidence-backed verification for generation, evaluation, smoke, and promotion-review paths when implementation changes;
- route new shared names, statuses, fields, or reason-code vocabularies through `trading-manager/scripts/` before cross-repository dependence.

Current Layer 1 verification gates include:

```bash
python3 -m compileall -q src scripts tests
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 scripts/models/model_01_market_regime/generate_model_01_market_regime.py --help
PYTHONPATH=src python3 scripts/models/model_01_market_regime/evaluate_model_01_market_regime.py --help
PYTHONPATH=src python3 scripts/models/model_01_market_regime/evaluate_model_01_market_regime.py
PYTHONPATH=src python3 scripts/models/model_01_market_regime/evaluate_model_01_market_regime.py --print-artifacts --output-json /tmp/l1_promotion_artifacts.json
PYTHONPATH=src python3 scripts/models/model_01_market_regime/evaluate_model_01_market_regime.py --from-database --output-json /tmp/l1_database_promotion_summary.json
PYTHONPATH=src python3 scripts/models/model_01_market_regime/run_market_regime_development_smoke.py --help
PYTHONPATH=src python3 scripts/models/model_01_market_regime/review_market_regime_promotion.py --help
PYTHONPATH=src python3 scripts/models/model_01_market_regime/review_market_regime_promotion.py --evaluation-summary-json /tmp/dev_smoke_summary.json --dry-run
PYTHONPATH=src python3 scripts/models/model_01_market_regime/review_market_regime_promotion.py --evaluation-summary-json /tmp/dev_smoke_summary.json --local-fallback-review --print-write-sql
git diff --check
```

Runtime SQL smoke tests require an explicitly configured PostgreSQL target and should not run as default unit tests.
