# Router Composite (Legacy / Transitional)

_Last updated: 2026-03-20_

## Status

This document is now **legacy / transitional context**, not the primary execution model.

The project previously emphasized a router/composite ownership model where one account was effectively treated as the main routed execution path while other strategies were compared around it.

That is **no longer the target architecture**.

## Current interpretation

Router/composite data is still useful as a comparison/debug layer, but it should now be treated as:
- historical context
- review/debug metadata
- transitional comparison output

and **not** as the canonical live execution model.

## What changed

The intended live model is now:
- all strategy accounts online simultaneously
- shared market/regime state
- parallel per-account execution
- review across all live accounts rather than only one routed account

Because of that change:
- `router_composite.selected_strategy` is no longer the only execution story that matters
- `position_owner` is no longer the core organizing principle for the whole runtime design
- review/reporting should gradually move away from router-centric semantics

## Still useful for now

While cleanup is still in progress, router/composite fields can still help answer:
- what the old router would have selected
- whether compare/debug output matches newer parallel execution results
- whether older reports are still reading transitional metadata correctly

## Going forward

Treat router-composite fields as:
- auxiliary comparison/debug context
- not the primary live-account execution truth

## Related docs

- `multi-account-parallel-execution.md`
- `execution-artifacts.md`
- `review-architecture.md`
