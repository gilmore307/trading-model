# model_03_target_state_vector

Contract-first workspace for `TargetStateVectorModel` / Layer 3.

Layer 3 has been reset from strategy-family/variant selection to target state-vector construction. It fuses market state, sector state, and anonymous target-local state into a point-in-time vector used by later layers.

This package should own the future importable implementation for:

- target state-vector schema helpers;
- feature block validation;
- target-state labels and baseline comparisons;
- evaluation evidence for market-only, market+sector, and market+sector+target state vectors.

Legacy strategy-family/variant code remains under `model_03_strategy_selection/` as frozen research history and compatibility material only.
