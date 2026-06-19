# Model 02 Target State

Status: deterministic pilot present; production promotion deferred.

## Role

`M02 Target State` owns target eligibility, ranking, target-specific state, and anonymous target candidate construction. It is the first target-aware model contract.

## Output

```text
model_02_target_state
  -> target_context_state
```

The output should preserve audit/routing metadata separately from model-facing fitting vectors. Raw ticker/company identity must not become a fitted feature.

Current local implementation emits:

- `target_context_state_ref`
- `background_context_state_ref`
- `target_context_state`
- `2_target_direction_score_<horizon>`
- `2_target_trend_quality_score_<horizon>`
- `2_target_path_stability_score_<horizon>`
- `2_target_noise_score_<horizon>`
- `2_target_transition_risk_score_<horizon>`
- `2_context_support_quality_score_<horizon>`
- `2_tradability_score_<horizon>`

## Inputs

- `background_context_state`.
- Anonymous target-local feature vectors.
- Point-in-time target liquidity, tradability, volatility, cost, optionability, event/risk, and quality evidence.
- Candidate-universe evidence available at or before `available_time`.

## Current Local Scripts

```text
scripts/models/model_02_target_state/generate_model_02_target_state.py
scripts/models/model_02_target_state/evaluate_model_02_target_state.py
scripts/models/model_02_target_state/review_target_state_promotion.py
```

These scripts produce fixture/local evidence only and must defer production activation.
