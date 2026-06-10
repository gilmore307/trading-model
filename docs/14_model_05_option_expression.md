# Model 05 Option Expression

Status: accepted current model contract; implementation migration required.

## Role

`M05 Option Expression` owns optional option/underlying expression after `M04 Unified Decision` has produced clean direct-underlying intent. It remains separate because option chains, liquidity, volatility, theta, spread, DTE, and structure constraints are a distinct domain.

## Output

```text
model_05_option_expression
  -> trading_guidance_record
  -> option_expression_plan / expression_vector
```

The model may choose underlying-only, long call, long put, no-option, or unavailable/not-applicable status according to accepted option-expression policy. Broker orders and account mutation remain outside `trading-model`.

## Inputs

- `unified_decision_vector`.
- Point-in-time option-chain snapshots, bid/ask, liquidity, IV, Greeks, DTE, spread, and conservative fill assumptions.

## Migration Source

Retired implementation package `model_09_option_expression` may be used as source material during migration. It is not a separate current model contract.
