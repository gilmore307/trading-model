# Model 01 Background Context

Status: accepted current model contract; implementation migration required.

## Role

`M01 Background Context` owns point-in-time broad market plus sector/industry background state. It replaces the older split between `MarketRegimeModel` and `SectorContextModel` as the current model standard.

## Output

```text
model_01_background_context
  -> background_context_state
```

The output should include structured market, sector, industry, liquidity, volatility, breadth, dispersion, stress, and data-quality heads. It must not choose final targets, actions, options, broker routes, or event-family parameters.

## Inputs

- Broad-market and cross-asset point-in-time features.
- Sector/industry/ETF/basket behavior features.
- Liquidity, volatility, breadth, correlation, crowding, dispersion, and macro-sensitive context.
- Only data available at or before `available_time`.

## Migration Source

Retired implementation packages `model_01_market_regime` and `model_02_sector_context` may be used as source material during migration. They are not separate current model contracts.
