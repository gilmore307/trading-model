# model_03_strategy_selection

Contract-first workspace for `StrategySelectionModel` / Layer 3.

Layer 3 scores which standalone strategy family and parameter-neighborhood variant fits an anonymous target candidate under current market and sector context. It does not own final entry/exit prices, option contract selection, position size, execution policy, or portfolio allocation.

Key files:

- `anonymous_target_candidate_builder/target_candidate_builder_contract.md` — Layer 3 candidate-preparation identity/anonymity contract that turns Layer 2 sector context into anonymous target candidates.
- `families/` — importable per-family strategy specs; one reviewed standalone strategy family per Python file, with deterministic variant expansion and stable spec hashes.
- `strategy_family_catalog.md` — reviewed strategy-family summary, suitable trading periods, parameter gradients, variant counts, and implementation notes.

Current status: active standalone family specs are implemented for one-by-one evaluation; signal scoring and promotion remain pending real-data tests.
