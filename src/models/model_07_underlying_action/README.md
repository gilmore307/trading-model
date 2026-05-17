# model_07_underlying_action

Current physical package for Layer 6 `UnderlyingActionModel` deterministic scaffold.

This package owns local/offline implementation for the accepted Layer 7 direct stock/ETF planned-action boundary:

- consumes conceptual Layer 4 `alpha_confidence_vector` refs/payloads;
- consumes conceptual Layer 5 `position_projection_vector` refs/payloads;
- accounts for current plus pending-adjusted direct-underlying exposure;
- applies hard/soft gates;
- resolves planned underlying action type;
- emits `underlying_action_plan` and `underlying_action_vector`;
- packages side-neutral entry, price-path, risk-plan, and conceptual Layer 7 trading-guidance handoff fields;
- never emits broker-order fields or option-contract selection fields.

Key files:

- `contract.py` — accepted constants, score families, planned action vocabulary, and forbidden output field names.
- `generator.py` — deterministic point-in-time scaffold for action-plan rows.
- `evaluation.py` — offline label helper for plan-quality evaluation; labels must not be joined into inference payloads.

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
