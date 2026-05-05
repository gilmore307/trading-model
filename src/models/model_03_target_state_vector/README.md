# model_03_target_state_vector

Contract-first workspace for `TargetStateVectorModel` / Layer 3.

Layer 3 has been reset from strategy-family/variant selection to target state-vector construction. It fuses market state, sector state, and anonymous target-local state into a point-in-time vector used by later layers.

Key files:

- `target_state_vector_contract.md` — V1 state-vector row identity, feature blocks, trailing windows, label families, baseline ladder, and rejection rules.
- `contract.py` — importable constants for the V1 block names, feature groups, label horizons, and baseline ladder.
- `anonymous_target_candidate_builder/` — candidate-preparation sub-boundary that creates anonymous target candidates before state-vector construction.

This package should own future importable implementation for:

- target state-vector schema helpers;
- feature block validation;
- target-state labels and baseline comparisons;
- evaluation evidence for market-only, market+sector, and market+sector+target state vectors.

Legacy strategy-family/variant code remains under `model_03_strategy_selection/` as frozen research history and compatibility material only.
