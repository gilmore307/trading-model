# Model 05 Option Expression

Status: accepted current model contract; deterministic implementation present; promotion evidence deferred.

## Role

`M05 Option Expression` owns optional option/underlying expression after `M04 Unified Decision` has produced clean direct-underlying intent. It remains separate because option chains, liquidity, volatility, theta, spread, DTE, and structure constraints are a distinct domain.

M05 does not own event-family identity or event-impact taxonomy. Option-sensitive event attributes, such as triple witching, expiry/gamma flow, volatility-surface dislocation, IV crush, and option liquidity/spread disruption, are governed by M06 and applied point-in-time by M03. M05 consumes those M03 event-state channels to decide expression consequences.

## Output

```text
model_05_option_expression
  -> option_expression_plan / expression_vector
```

The model may choose underlying-only, long call, long put, no-option, or unavailable/not-applicable status according to accepted option-expression policy. Broker orders and account mutation remain outside `trading-model`.

## Inputs

- `unified_decision_vector`.
- `direct_underlying_intent` from M04.
- `event_state_vector` from M03, including option-price, volatility-surface, option-liquidity/spread, and expiry/gamma-flow impact channels.
- Point-in-time option-chain snapshots, bid/ask, liquidity, IV, Greeks, DTE, spread, and conservative fill assumptions.

## Training vs Live Invocation

Historical training/evaluation should preserve full-minute M04 thesis coverage. Minutes with unavailable option chains, non-optionable instruments, direct-underlying-only routes, or crypto routes should emit explicit `no_option_expression` / `not_option_applicable` status evidence instead of fabricated option selections.

Live execution may invoke the heavier option-expression component only when M04 produces an option-expression-relevant thesis and option-chain context is available.

## Migration Source

Retired implementation package `model_05_option_expression` may be used as source material during migration. It is not a separate current model contract.

## Current Gate

The current implementation lives in `src/models/model_05_option_expression/` and local generate/evaluate/review entrypoints live under `scripts/models/model_05_option_expression/`. It consumes M04 `direct_underlying_intent` / `unified_decision_vector_ref`, emits `5_*` option-expression fields, and does not expose retired `underlying_action_plan` outputs. Production promotion still requires option-chain replay labels, cost/fill/theta/IV validation, baseline comparison, leakage checks, and manager-side promotion review.
