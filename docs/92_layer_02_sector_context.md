# Layer 02 - SectorContextModel

This file records the current `trading-model` contract for Layer 2.

## Input

```text
market_context_state
trading_data.feature_02_sector_context
```

Layer 1 market context is conditioning context only. Layer 2 consumes sector/industry ETF behavior evidence from `feature_02_sector_context`. ETF holdings and `stock_etf_exposure` belong downstream to anonymous target candidate construction, not Layer 2 core behavior modeling.

## Physical artifacts

```text
trading_model.model_02_sector_context
trading_model.model_02_sector_context_explainability
trading_model.model_02_sector_context_diagnostics
```

## `model_02_sector_context` - output

The primary output is the narrow, stable downstream contract. It contains identity, trend/context stability state, downstream sector handoff, and eligibility/quality summary fields:

```text
available_time
sector_or_industry_symbol
model_id
model_version
market_context_state_ref
2_trend_stability_score
2_trend_certainty_score
2_context_conditioned_stability_score
2_selection_readiness_score
2_sector_handoff_state
2_sector_handoff_rank
2_sector_handoff_reason_codes
2_eligibility_state
2_eligibility_reason_codes
2_state_quality_score
2_evidence_count
```

Allowed `2_sector_handoff_state` values are:

```text
selected | watch | blocked | insufficient_data
```

## `model_02_sector_context_explainability` - explainability

Explainability owns human-review detail that should not become a hard downstream dependency:

- observed behavior internals such as relative strength, trend direction, volatility-adjusted trend, breadth, dispersion, correlation, and chop;
- inferred attribute internals such as growth/defensive/cyclical/rate/dollar/commodity/risk-appetite sensitivity and attribute certainty;
- conditional behavior internals such as beta, directional coupling, volatility response, capture asymmetry, response convexity, context support, and transition sensitivity;
- contributing evidence and reason-code detail.

## `model_02_sector_context_diagnostics` - diagnostics

Diagnostics owns acceptance, monitoring, and gating evidence:

- liquidity/spread/optionability/capacity/tradability;
- event/gap/volatility/correlation stress and downside-tail risk;
- coverage/freshness/missingness;
- baseline comparison;
- refit stability;
- no-future-leak checks.

## Naming rule

Layer 2 model fields use compact `2_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading column names when needed rather than storing semantic aliases such as `layer02_*`.
