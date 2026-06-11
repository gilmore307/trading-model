# model_08_underlying_action

Physical package for Layer 8 `UnderlyingActionModel`.

This package owns local/offline implementation for the accepted Layer 8 direct underlying/spot planned-action boundary across stock, ETF, or crypto-style candidates:

- consumes Layer 5 `alpha_confidence_vector` refs/payloads;
- consumes Layer 7 `position_projection_vector` refs/payloads;
- accounts for current plus pending-adjusted direct-underlying exposure;
- applies hard/soft gates;
- resolves planned underlying action type;
- emits `underlying_action_plan` and `underlying_action_vector`;
- packages side-neutral entry, price-path, risk-plan, and M05 option-expression handoff fields;
- never emits broker-order fields or option-contract selection fields.

Key files:

- `contract.py` — accepted constants, score families, planned action vocabulary, and forbidden output field names.
- `generator.py` — point-in-time generator for action-plan rows.
- `evaluation.py` — offline label helper for plan-quality evaluation; labels must not be joined into inference payloads.

Training should use dense minute-level underlying-action state rows whenever Layer 7 projection plus point-in-time underlying quote/liquidity/policy context exist. Planned-action triggers and hard gates are outputs or routing policies, not training-row admission filters.

Layer 8 owns conservative planned-action gating. It should prefer `maintain` or `no_trade` unless Layer 7 position gap, utility lift, cost, risk-budget fit, stability, confidence, pending-adjusted exposure, and current underlying quote/liquidity/borrow evidence jointly support an open/increase/reduce/close/cover plan.

Boundary:

```text
planned underlying action != broker order
planned quantity != final order quantity
entry plan != order type
stop_loss_price != broker stop order
take_profit_price != broker limit order
underlying action plan != option expression
underlying action plan != live execution
```
