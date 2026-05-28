# model_03_target_state_vector

Contract-first workspace for `TargetStateVectorModel` / Layer 3.

Layer 3 is direction-neutral target context/state-vector construction plus anonymous candidate-set ranking for target handoff. Layer 3 preprocessing first produces anonymous target candidates and `anonymous_target_feature_vector` inputs; `TargetStateVectorModel` then fuses market state, sector state, and anonymous target-local state into the point-in-time `target_context_state` used by later layers. Signed current-state direction, tradability, transition risk, noise, liquidity/cost, row quality, and target handoff rank remain separate; Layer 3 does not output event context, alpha confidence, position size, option expression, or final trade action.

Task execution may remain target-major across folds because routing symbols only supply anonymous samples. Evaluation and promotion must still aggregate by fold and by the fixed candidate-universe policy used in live routing.

Key files:

- `target_state_vector_contract.md` — target-context/state-vector row identity, feature blocks, trailing windows, label families, baseline ladder, and rejection rules.
- `contract.py` — importable constants for block names, feature groups, label horizons, and baseline ladder.
- `anonymous_target_candidate_builder/` — candidate-preparation sub-boundary that creates anonymous target candidates before state-vector construction.

Current importable implementation:

- `anonymous_target_candidate_builder/builder.py` — builds anonymous target candidate rows and validates that the model-facing `anonymous_target_feature_vector` excludes raw identity and downstream action/label leakage.
- `generator.py` — turns `feature_03_target_state_vector` rows into `model_03_target_state_vector` rows with separated signed direction, direction-neutral tradability, transition/noise risk, liquidity, state quality, embedding, cluster, and diagnostics.
- `evaluation.py` — builds local/fixture promotion evidence over the accepted baseline ladder: market-only, market+sector, and market+sector+target vector. Labels follow the real Layer 3 route: future path quality, forward path risk, liquidity/tradability outcome, and state-transition quality.
- `config/promotion_thresholds.toml` — production promotion threshold defaults for real-data review.

Local/fixture evidence is useful for contract tests but must defer production promotion until real-data evaluation, split stability, baseline improvement, leakage checks, and reviewed approval are all present.
