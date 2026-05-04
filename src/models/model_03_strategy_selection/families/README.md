# families

Implementation package for reviewed standalone `StrategySelectionModel` strategy families.

Each strategy owns one Python file with:

- reviewed family/group/status metadata;
- fixed parameters that do not multiply variants;
- variable axes that deterministically expand into `3_strategy_variant` specs;
- stable `3_strategy_variant` and `strategy_spec_hash` generation.

Boundary:

- This package implements Layer 3 family/variant specs only.
- It consumes anonymous target-candidate features during evaluation; it must not consume raw ticker/company identity.
- It does not emit entry/exit orders, option contract selection, DTE, strike, delta, premium, Greeks, size, portfolio allocation, or execution policy.
- Backlog, modifier, meta, position-management, and option-expression families remain in `strategy_family_catalog.md` until promoted into this package.
