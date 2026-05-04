# families

Implementation package for reviewed standalone `StrategySelectionModel` strategy families.

Files are numbered in first evaluation order:

- `family_spec_common.py` owns shared primitives only.
- `family_01_*` through `family_10_*` are active standalone family specs in one-by-one test order.

Each strategy owns one Python file with:

- reviewed family/status metadata and explicit `3_family_evaluation_order`;
- fixed parameters that do not multiply variants;
- variable axes that deterministically expand into `3_strategy_variant` specs;
- stable `3_strategy_variant` and `strategy_spec_hash` generation from family plus fixed/variable parameters; evaluation order does not affect the variant hash.

Boundary:

- This package implements Layer 3 family/variant specs only.
- Standalone evaluation, pruning, and promotion decisions are made at `3_strategy_family` granularity.
- It consumes anonymous target-candidate features during evaluation; it must not consume raw ticker/company identity.
- It does not emit entry/exit orders, option contract selection, DTE, strike, delta, premium, Greeks, size, portfolio allocation, or execution policy.
- Backlog, modifier, meta, position-management, and option-expression families remain in `strategy_family_catalog.md` until promoted into this package.

Variant lifecycle:

- Family specs define the reviewed searchable variant universe, not necessarily the exact subset used for model training.
- Strategy simulation and review advance in natural-month batches.
- Monthly review scripts may propose gradient expansion when adjacent options suggest an untested optimum between them.
- Monthly review scripts may propose retiring variants from the active training subset only when they lack conditional edge across reviewed market/sector/target states or are dominated by neighboring variants in the same conditions.
- Weak aggregate monthly return alone is not a pruning reason; rare-regime variants can remain valuable if they approach oracle performance under specific states.
- Final expansion, pruning, strategy-library promotion, and model-training promotion decisions must be accepted by an agent reviewer; scripts assemble evidence and recommendations, but do not independently approve active-universe or promotion changes.
