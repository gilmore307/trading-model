# Vector and State Taxonomy

Status: accepted vocabulary for the current five-model stack

## Vocabulary

| Term | Meaning |
|---|---|
| feature surface | Point-in-time input rows/artifacts eligible for model-facing feature construction. |
| feature vector | Model-facing input representation `X`; labels/outcomes are excluded. |
| state | Narrow model output describing an interpretable condition at `available_time`. |
| state vector | Block-structured model output state. |
| score | Scalar dimension inside a state/vector. |
| label / outcome | Training/evaluation-only future evidence; never an inference feature. |
| diagnostics | Acceptance, monitoring, missingness, calibration, leakage, and quality evidence. |
| explainability | Human-review support: feature attribution, reason codes, and evidence refs. |
| probabilistic factor | A layer-owned PIT probability/logit/uncertainty/gate contribution that stays inside that layer's evidence boundary. |

## Current Model Outputs

| Model | Primary output vocabulary |
|---|---|
| `M01 Background Context` | `background_context_state` |
| `M02 Target State` | `target_context_state` |
| `M03 Event State` | `event_state_vector` |
| `M04 Unified Decision` | `thesis_distribution_surface`, derived `unified_decision_vector` |
| `M05 Option Expression` | `expression_probability_surface`, derived `option_expression_plan`, `expression_vector` |

## Model-Specific Notes

### M01 Background Context

M01 describes broad market plus sector/industry background. It may expose market, sector, industry, liquidity, volatility, breadth, dispersion, stress, and data-quality score families. It must not rank final targets, choose actions, select option contracts, or mutate event-family parameters.

### M02 Target State

M02 owns target eligibility, ranking, and anonymous target-state evidence. `anonymous_target_feature_vector` is an input feature vector for target-state fitting, not a final model output. Raw ticker/company identity is audit/routing metadata and must not become a fitted feature. M02 may consume M01 as fixed context, but its output must remain the target residual factor; it must not re-count M01 market/background contribution as target alpha.

### M03 Event State

M03 owns event-conditioned response/risk state from accepted event contracts. It may emit response strength, response direction tendency, uncertainty, path risk, entry/cap/disable pressure, applicability confidence, and distribution-effect channels. It must not emit standalone event alpha, component-control actions, or mutate event taxonomy/effect-model parameters. M03 may consume M01/M02 as fixed applicability context, but its output must remain the event residual factor; it must not re-count market/background or target-base contribution.

### M04 Unified Decision

M04 owns one direct-underlying decision vector with structured heads:

```text
edge / after-cost alpha
risk policy and constraints
exposure / size / position projection
direct-underlying action thesis
no-trade and invalidation profile
```

These heads are fields of one current model contract, not separate current model contracts.

M04 is the only owner of calibrated fusion across M01-M03 factors. Cross-factor
interaction, final trade posterior, final action threshold, and no-trade
calibration belong here, not inside M01-M03.

### M05 Option Expression

M05 owns optional option/underlying expression after M04 direct-underlying intent exists. It is offline guidance only and must not become broker execution.

### M03 Event-Governance Tooling

M03 event-governance tooling prepares taxonomy, modelability, impact-window, residual-attribution, and packet evidence for M03 `event_effect_model` work. It is not a model output vocabulary and must not emit runtime component actions such as warn, cap, block, reduce, or flatten.

## Compatibility Boundary

Current model-facing payloads use only the M01-M05 vocabulary above. Historical artifact names belong to immutable evidence or Git history, not active contracts, scripts, docs, or model outputs.
