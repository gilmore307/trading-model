# model_03_target_state_vector

Contract-first workspace for `TargetStateVectorModel` / Layer 3.

Layer 3 is direction-neutral target context/state-vector construction. Layer 3 preprocessing first produces anonymous target candidates and `anonymous_target_feature_vector` inputs; `TargetStateVectorModel` then fuses market state, sector state, and anonymous target-local state into the point-in-time `target_context_state` used by later layers. Signed current-state direction, tradability, transition risk, noise, liquidity/cost, and row quality remain separate; Layer 3 does not output event context, alpha confidence, position size, or final trade action.

Key files:

- `target_state_vector_contract.md` — V1 target-context/state-vector row identity, feature blocks, trailing windows, label families, baseline ladder, and rejection rules.
- `contract.py` — importable constants for the V1 block names, feature groups, label horizons, and baseline ladder.
- `anonymous_target_candidate_builder/` — candidate-preparation sub-boundary that creates anonymous target candidates before state-vector construction.

Current importable implementation:

- `anonymous_target_candidate_builder/builder.py` — builds anonymous target candidate rows and validates that the model-facing `anonymous_target_feature_vector` excludes raw identity and downstream action/label leakage.
- `generator.py` — turns `feature_03_target_state_vector` rows into `model_03_target_state_vector` rows with separated signed direction, direction-neutral tradability, transition/noise risk, liquidity, state quality, embedding, cluster, and diagnostics.
- `evaluation.py` — builds local/fixture promotion evidence over the accepted baseline ladder: market-only, market+sector, and market+sector+target vector.
- `config/promotion_thresholds.toml` — production promotion threshold defaults for real-data review.

Local/fixture evidence is useful for contract tests but must defer production promotion until real-data evaluation, split stability, baseline improvement, leakage checks, and reviewed approval are all present.

