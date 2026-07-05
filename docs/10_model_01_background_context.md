# Model 01 Background Context

Status: deterministic pilot present; production promotion deferred.

## Role

`M01 Background Context` owns point-in-time broad market plus sector/industry background state. It replaces the older split between `MarketRegimeModel` and `SectorContextModel` as the current model standard.

## Output

```text
model_01_background_context
  -> background_context_state
```

The output should include structured market, sector, industry, liquidity, volatility, breadth, dispersion, stress, and data-quality heads. It must not choose final targets, actions, options, broker routes, or event-family parameters.

M01 owns only the market/background factor. It must not include M02 target
selection evidence, M03 event evidence, M04 final decision evidence, or M05
expression evidence in its model-facing output.

Current local implementation emits:

- `background_context_state_ref`
- `background_context_state`
- `1_market_direction_score_<horizon>`
- `1_market_trend_quality_score_<horizon>`
- `1_market_risk_stress_score_<horizon>`
- `1_market_liquidity_support_score_<horizon>`
- `1_market_volatility_pressure_score_<horizon>`
- `1_sector_breadth_score_<horizon>`
- `1_sector_dispersion_score_<horizon>`
- `1_background_context_quality_score_<horizon>`

## Inputs

- Broad-market and cross-asset point-in-time features.
- Sector/industry/ETF/basket behavior features.
- Liquidity, volatility, breadth, correlation, crowding, dispersion, and macro-sensitive context.
- Only data available at or before `available_time`.

## Review Path

Post-replay review must score M01 independently at replay-time background-state
granularity. The review joins each published `background_context_state` to
market/context outcome labels for the same replay timestamp and horizon. Missing
joined labels are a review evidence gap, not evidence that M04 is responsible.

If M01 rows are independently acceptable while final selected trades perform
poorly, attribution moves downstream to M04 fusion/thresholding unless M02 or
M03 has its own local defect or an explicit handoff defect is shown.

## Current Local Scripts

```text
scripts/models/model_01_background_context/generate_model_01_background_context.py
scripts/models/model_01_background_context/evaluate_model_01_background_context.py
scripts/models/model_01_background_context/review_background_context_promotion.py
```

These scripts produce fixture/local evidence only and must defer production activation.
