# Vector and State Taxonomy

Status: accepted vocabulary for the current six-model stack

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

## Current Model Outputs

| Model | Primary output vocabulary |
|---|---|
| `M01 Background Context` | `background_context_state` |
| `M02 Target State` | `target_context_state` |
| `M03 Event State` | `event_state_vector` |
| `M04 Unified Decision` | `unified_decision_vector` |
| `M05 Option Expression` | `option_expression_plan`, `expression_vector` |
| `M06 Residual Event Governance` | `event_risk_intervention`, future event-family packet eligibility |

## Model-Specific Notes

### M01 Background Context

M01 describes broad market plus sector/industry background. It may expose market, sector, industry, liquidity, volatility, breadth, dispersion, stress, and data-quality score families. It must not rank final targets, choose actions, select option contracts, or mutate event-family parameters.

### M02 Target State

M02 owns target eligibility, ranking, and anonymous target-state evidence. `anonymous_target_feature_vector` is an input feature vector for target-state fitting, not a final model output. Raw ticker/company identity is audit/routing metadata and must not become a fitted feature.

### M03 Event State

M03 owns event-conditioned response/risk state from accepted event contracts. It may emit response strength, response direction tendency, uncertainty, path risk, entry/cap/disable pressure, and applicability confidence. It must not emit standalone event alpha or change M06 event parameters.

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

### M05 Option Expression

M05 owns optional option/underlying expression after M04 direct-underlying intent exists. It is offline guidance only and must not become broker execution.

### M06 Residual Event Governance

M06 owns missed-event checks, residual event-risk intervention, attribution, and future event-family packet eligibility. It may warn, cap, block, review, or nominate reduce/flatten review actions, but it must not send orders or mutate accounts.

## Retired Vocabulary

Old `market_context_state`, `context_etf_state`, `event_failure_risk_vector`, `alpha_confidence_vector`, `dynamic_risk_policy_state`, `position_projection_vector`, `underlying_action_plan`, and `event_context_vector` names may appear in retained implementation packages and historical artifacts. They are migration-source vocabulary, not the current six-model contract standard.
