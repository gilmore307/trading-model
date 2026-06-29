# Model Learning Design

Status: accepted six-model learning route; implementation is evidence-gated
Owner intent: reduce serial model-error propagation while preserving the live/paper components needed for target selection, event reasoning, direct decision, option expression, and residual event governance.

## Core Principle

Each model contract must do exactly one of these jobs:

- estimate a point-in-time conditional distribution or calibrated score;
- optimize a declared utility or policy under constraints;
- enforce deterministic hard constraints, accounting, timestamps, schemas, and safety gates;
- produce post-hoc attribution or future evidence packets.

A model contract must not mix prediction, policy, hard enforcement, and attribution in the same score. Deterministic code may own contracts, feature assembly, timestamps, schemas, safety gates, and validation checks. It must not preserve an alternate scoring route for a contract whose current role is trained estimation or policy optimization.

Learned-model design is direct-to-final. Do not introduce temporary learned contracts, compatibility bridges, or learned-looking deterministic substitutes for any learned model. A final-contract artifact may pass through lifecycle evidence states such as `defined`, `trained_offline`, `replay_validated`, `shadow_candidate`, `promoted`, or `rejected`; those states are evidence gates, not architecture versions. Only promoted artifacts may affect production decisions.

## Current Learning Route

| Model | Active learned scheme | Learning role |
|---|---|---|
| `M01` Background Context | `continual_gru_context_estimator` | CPU-friendly short-window sequence estimator for shared market/sector/industry context and regime persistence. |
| `M02` Target State | `continual_pairwise_residual_mlp_target_ranker` | Pairwise/listwise anonymous target eligibility, ranking, and target-state estimator. |
| `M03` Event State | `continual_gru_event_risk_scorer` | CPU-friendly short-window sequence scorer for event-conditioned response/risk, event decay, and event-cluster state under frozen event-governance contracts. |
| `M04` Unified Decision | `continual_residual_mlp_policy_value` | Direct downstream decision/utility model with structured edge, risk, exposure, no-trade, and action heads. |
| `M05` Option Expression | `continual_residual_mlp_option_chain_ranker` | Separate option/expression utility ranker consuming clean direct-underlying decision intent and point-in-time option-chain context. |
| `M06` Residual Event Governance | `continual_gru_residual_risk_gate` | CPU-friendly short-window residual-risk sequence gate for residual event governance, attribution, intervention, and future-packet routing. |

The active scheme choices are not promotion claims. GRU is selected where sequence memory and state persistence are central to the layer. Residual MLP is selected where nonlinear dense-state interaction or structured ranking is central to the layer. Transformer-style attention is not the active route on the current CPU-only server.

## Cross-Model Rules

- Model-facing inputs must be point-in-time at `available_time`.
- Training coverage and live invocation are separate. Historical training/evaluation should preserve full-minute state coverage wherever inputs can be constructed, including neutral, no-event, no-action, structural no-option, temporary option-chain-missing, and no-intervention states. Live routing may still gate expensive or optional components, such as invoking M05 only after M04 produces option-expression intent.
- Labels and outcomes are training/evaluation-only and must never enter inference vectors.
- Real ticker/company identity remains audit/routing metadata, not a fitting feature.
- Stable identity surrogates must be tested, not only banned by column name.
- Score thresholds should not hide model weakness. Where a score has a natural neutral point, training should produce that score directly.
- M06 same-fold discoveries are quarantined from same-fold upstream training. Accepted discoveries may become future M03 inputs only after evidence packet review.
- Validation must beat a realistic baseline, not just show historical fit.

## Full-Minute Training Coverage

The accepted training stance is full-minute coverage with model-specific applicability semantics.

Every eligible historical minute should enter the point-in-time training/evaluation ledger for the current chain when required inputs can be constructed. Blank time is not absence of data; it is a learnable state. No-event, no-trade, maintain, no-option, and no-intervention rows are part of the supervised problem because most live market time is inactive.

This does not require every model component to be invoked in the same way during live execution. Live routing may skip or defer optional components for latency, cost, or applicability reasons. The training ledger should still preserve the corresponding state:

```text
M03: no event -> explicit neutral/no-event event_state_vector
M04: no action -> explicit no_trade or maintain decision state
M05: structural no optionability -> `non_optionable_underlying` with direct-underlying/no-option expression state; temporary missing chain -> `optionable_chain_missing`; neither may become fabricated option selection or zero-valued option signal
M06: uncertain attribution -> explicit low_confidence / no_intervention / attribution_unknown state
```

Training loss, metrics, and promotion evidence may still use masks, weights, and sub-buckets so rare event/action/option/intervention cases are not drowned by neutral minutes. Those masks are optimization and reporting controls; they are not permission to remove blank minutes from the point-in-time ledger.

## Replayable Cumulative Learning Lifecycle

The accepted model stack is closed loop as an evidence lifecycle and uses replayable cumulative learning as the long-term training route. Model families are chosen per layer, but every learned layer must support point-in-time updates, immutable checkpoints, replay restore, rollback, and promotion-gated deployment. A cumulative learner may absorb new finalized samples over time; it must not update same-fold inference state from future labels or downstream outcomes.

The loop has three separate paths:

```text
Inference path:
  point-in-time inputs -> M01 -> M02 -> M03 -> M04 -> optional M05 -> M06

Evaluation path:
  fold/replay settles -> future labels, utilities, diagnostics, and residuals are joined after the fact

Promotion feedback path:
  finalized evaluation evidence -> review/promotion gate -> later checkpoint update, shadow promotion, or rejection
```

No future label, realized utility, downstream failure, broker outcome, same-fold M06 discovery, or post-event interpretation may feed back into the same fold's inference features. A model can learn from failure only through finalized training events, frozen artifact lineage, immutable checkpoints, and accepted review gates.

Every cumulative model backend must expose the same control contract:

```text
predict(as_of_time, state_vector, checkpoint)
update(as_of_time, finalized_training_events)
checkpoint(as_of_time)
restore(checkpoint_id)
replay(start_time, end_time, checkpoint_seed)
audit(sample_id)
```

Feature normalizers, scalers, embeddings, and label joins are part of the model state. They must be checkpointed and replayed point-in-time; they may not be fit on future data and reused for earlier replay clocks.

Fold-scoped training checkpoints are cumulative state, not isolated fold fits. The first eligible fold may cold start from its approved feature contract. Each later fold must restore the previous fold checkpoint, keep the checkpointed feature scaler/state as the seed state, update only on finalized training events available to the new fold's training window, and write a new checkpoint whose parent points to the immediately previous fold checkpoint.

M06 has one special feedback route:

```text
M04/M05 replay failure
  -> M06 residual event attribution
  -> reviewed event-family or strategy-failure packet
  -> future M03 candidate training/evaluation
  -> future-fold M03 acceptance only after review
```

M06 must not become a generic hindsight corrector. It owns residual event attribution, intervention utility, and future M03 packet eligibility only. Non-event model misses remain the evaluation/promotion evidence of their owning model.

M03 consumes accepted M06 focus-pool event contracts as frozen qualitative/time-parameter inputs. M06 owns event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, and later demotion/split/reweight/parameter revision. M03 owns only the quantitative conditional response and failure-risk mapping inside that frozen contract. It may output event-conditioned response strength, direction tendency, uncertainty, failure risk, path risk, entry/cap/disable pressure, and evidence/applicability confidence; it must not output standalone event alpha or change M06 event parameters.

M04 must consume reviewed M03 event-conditioning fields as formal inputs and let training learn their weight, sign, uncertainty, risk penalty, or near-zero contribution. Event-family removal, demotion, split, or time-window revision remains an M06/M03 review outcome, not a no-event baseline substitution. A no-M03 decision baseline is not a default evaluation route unless M04/M05/M06 are also rerun as a full counterfactual chain.

| Model | Inference dependency | Primary output | Label / utility source after fold close | Feedback owner | Forbidden feedback |
|---|---|---|---|---|---|
| `M01` Background Context | Broad-market, sector/industry, liquidity, volatility, and macro-sensitive point-in-time features. | `background_context_state` | Future broad/sector state, volatility, liquidity, transition, downstream calibration-lift labels. | M01 evaluation and promotion evidence. | Target choices, action labels, portfolio outcomes, and future market/sector labels as same-fold inputs. |
| `M02` Target State | `background_context_state` plus anonymous target-local features and candidate policy. | `target_context_state` | Future target path, persistence/reversion, liquidity/tradability, state-transition, and candidate-ranking labels. | M02 evaluation and promotion evidence. | Raw ticker/company identity, future selected-target outcomes, alpha/action labels, and downstream trade results as same-fold inputs. |
| `M03` Event State | Background/target state plus accepted event-family or strategy-failure evidence and frozen M06 focus-pool event contracts. | `event_state_vector` | Reviewed event-conditioned response, uncertainty, strategy-failure, entry-block, exposure-cap, disable, path-risk, and session-gap labels. | M03 evaluation and event-strategy promotion review; contract-stress diagnostics route back to M06. | Raw news/provider text, unreviewed event candidates, same-fold M06 residual attribution, standalone event-alpha labels, M06 event-parameter mutation, and future realized impact labels as same-fold inputs. |
| `M04` Unified Decision | Background, target, event state, quality/calibration evidence, replay-safe portfolio/risk context, cost/friction, quote/liquidity/borrow, and exposure state. | `unified_decision_vector` | After-cost alpha, residual return, downside/path risk, portfolio/risk-budget utility, exposure regret, no-trade/maintain calibration, action utility, fill-realism, churn, and path labels. | M04 unified decision evaluation and promotion evidence. | Account/broker mutation, future returns as inference fields, future event revisions, order/fill outcomes as inference features, historical action imitation, final order quantities, option contract choice, alpha relearning inside action heads, and hard-limit overrides. |
| `M05` Option Expression | Completed M04 decision intent plus option-surface status, timestamped option candidates, and option exposure context. | `option_expression_plan` and `expression_vector` when optionable. | Candidate expression utility, realistic option after-cost return, fill/slippage/theta/IV, underlying-only labels for evaluated option surfaces, and no-option status labels for unavailable routes. | M05 option replay evaluation and promotion evidence. | Best-contract hindsight, future option paths, realized fills, broker order ids, final quantities, and same-fold M06 discoveries. |
| `M06` Residual Event Governance | M01-M05 thesis context plus point-in-time event observations, scope mapping, and residual-event evidence. | `event_risk_intervention` / future packet eligibility. | Residual intervention utility, attribution correctness, tail-failure reduction, overblock cost, and event-family packet labels. | M06 residual evaluation, event-family review, and future M03 packet routing. | Same-fold upstream feature mutation, automatic M03 promotion, standalone event alpha, broker/account mutation, and generic non-event model correction. |

The loop is closed only when every emitted field can be classified as one of:

```text
inference input
primary output
label / utility
diagnostic
explainability
validation evidence
review packet
```

Any field that is both a future label and a same-fold inference input breaks the contract.

## Redesign Risks

The main risk is target entanglement. M04 and M05 can accidentally learn "the trade that would have made money." Their runtime heads must stay separate:

```text
M04 edge head estimates after-cost edge.
M04 risk head sets portfolio/risk policy.
M04 exposure head projects desired exposure.
M04 action head chooses the direct-underlying action thesis.
M05 option-expression model chooses the expression.
```

Policy and expression models require stronger validation than ordinary supervised models. M04 and M05 must use walk-forward replay, off-policy evaluation where applicable, and sensitivity checks for costs, fills, turnover, and liquidity.

M06 must not become a hindsight oracle. Residual discoveries from replay are attribution and future evidence, not same-fold upstream features.

## Minimal Implementation Gate

Before expanding a model implementation, define its objective contract:

1. primary target or utility;
2. prediction horizon;
3. label construction and cost assumptions;
4. inputs allowed at `available_time`;
5. forbidden inputs;
6. baseline to beat;
7. walk-forward validation metric;
8. leakage test;
9. downstream consumer.

Then trace one historical fold row through M01-M06. Every emitted field must be classifiable as estimate, policy output, hard gate, diagnostic, explainability, or attribution. Any field that mixes score, policy, reason, and constraint should be split before implementation proceeds.

Framework selection is accepted in `docs/24_model_framework_readiness.md`: M01/M03/M06 use CPU-friendly GRU schemes, while M02/M04/M05 use residual-MLP schemes. Promotion remains a later evidence gate; selected schemes still need layer-specific labels, point-in-time replay, leakage checks, calibration, checkpoint restore, rollback evidence, and downstream-neutral or downstream-positive full-chain validation.
