# families

Implementation package for reviewed standalone `StrategySelectionModel` strategy families.

Files are numbered in first evaluation order:

- `family_00_common.py` owns shared primitives only.
- `family_01_*` through `family_10_*` are active standalone family specs in one-by-one test order.

Each strategy owns one Python file with:

- reviewed family/status metadata and explicit `3_family_evaluation_order`;
- `3_strategy_group` as descriptive taxonomy only, not a pruning or promotion unit;
- fixed parameters that do not multiply variants;
- variable axes that deterministically expand into `3_strategy_variant` specs;
- stable `3_strategy_variant` and `strategy_spec_hash` generation from family plus fixed/variable parameters; taxonomy and evaluation order do not affect the variant hash.

Boundary:

- This package implements Layer 3 family/variant specs only.
- Standalone evaluation, pruning, and promotion decisions are made at `3_strategy_family` granularity.
- It consumes anonymous target-candidate features during evaluation; it must not consume raw ticker/company identity.
- It does not emit entry/exit orders, option contract selection, DTE, strike, delta, premium, Greeks, size, portfolio allocation, or execution policy.
- Backlog, modifier, meta, position-management, and option-expression families remain in `strategy_family_catalog.md` until promoted into this package.
