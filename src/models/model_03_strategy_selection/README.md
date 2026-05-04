# model_03_strategy_selection

Contract-first workspace for `StrategySelectionModel` / Layer 3.

Layer 3 scores which standalone strategy family and parameter-neighborhood variant fits an anonymous target candidate under current market and sector context. It does not own final entry/exit prices, option contract selection, position size, execution policy, or portfolio allocation.

Key files:

- `anonymous_target_candidate_builder/target_candidate_builder_contract.md` — Layer 3 candidate-preparation identity/anonymity contract that turns Layer 2 sector context into anonymous target candidates.
- `families/` — importable numbered per-family strategy specs; `family_spec_common.py` owns shared primitives and `family_01_*` through `family_10_*` follow first evaluation order, with deterministic variant expansion and stable spec hashes.
- `strategy_family_catalog.md` — reviewed strategy-family summary, suitable trading periods, parameter gradients, variant counts, and implementation notes.

Current status: active standalone family specs are implemented for one-by-one evaluation. Per-bar strategy variant simulation should be produced by `trading-data` as `feature_03_strategy_variant_simulation` from `trading-manager` requests; this package consumes those features for oracle construction, lifecycle review, model selection, and promotion evidence.
