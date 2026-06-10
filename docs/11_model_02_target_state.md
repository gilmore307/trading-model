# Model 02 Target State

Status: accepted current model contract; implementation migration required.

## Role

`M02 Target State` owns target eligibility, ranking, target-specific state, and anonymous target candidate construction. It is the first target-aware model contract.

## Output

```text
model_02_target_state
  -> target_context_state
```

The output should preserve audit/routing metadata separately from model-facing fitting vectors. Raw ticker/company identity must not become a fitted feature.

## Inputs

- `background_context_state`.
- Anonymous target-local feature vectors.
- Point-in-time target liquidity, tradability, volatility, cost, optionability, event/risk, and quality evidence.
- Candidate-universe evidence available at or before `available_time`.

## Migration Source

Retired implementation package `model_03_target_state_vector` may be used as source material during migration. It is not a separate current model contract.
