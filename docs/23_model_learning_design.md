# Model Learning Design

Status: accepted learning route; implementation is evidence-gated
Owner intent: each layer must have one clear role before its implementation is expanded.

## Core Principle

Each layer must do exactly one of these jobs:

- estimate a point-in-time conditional distribution or calibrated score;
- optimize a declared utility or policy under constraints;
- enforce deterministic hard constraints, accounting, timestamps, schemas, and safety gates;
- produce post-hoc attribution or future evidence packets.

A layer must not mix prediction, policy, hard enforcement, and attribution in the same score. Deterministic code may own contracts, feature assembly, timestamps, schemas, safety gates, and validation checks. It must not preserve an alternate scoring route for a layer whose current contract is trained estimation or policy optimization.

Learned-layer design is direct-to-final. Do not introduce temporary learned contracts, compatibility bridges, or learned-looking deterministic substitutes for any learned layer. A final-contract artifact may pass through lifecycle evidence states such as `defined`, `trained_offline`, `replay_validated`, `shadow_candidate`, `promoted`, or `rejected`; those states are evidence gates, not architecture versions. Only promoted artifacts may affect production decisions.

Layers 1-5 are conditional estimators and calibrators, not policy optimizers. Their final contracts should specify point-in-time inputs, labels, artifact evidence, explainability, and validation gates without forcing the candidate-utility/policy language used by Layers 6-10.

## Cross-Layer Rules

- Model-facing inputs must be point-in-time at `available_time`.
- Labels and outcomes are training/evaluation-only and must never enter inference vectors.
- Real ticker/company identity remains audit/routing metadata, not a fitting feature.
- Stable identity surrogates must be tested, not only banned by column name.
- Score thresholds should not hide model weakness. Where a score has a natural neutral point, training should produce that score directly.
- Layer 10 same-fold discoveries are quarantined from same-fold upstream training. Accepted discoveries may become future Layer 4 inputs only after evidence packet review.
- Validation must beat a realistic baseline, not just show historical fit.

## Closed-Loop Evidence Lifecycle

The accepted model stack is closed loop as an evidence lifecycle, not as a live recursive model loop and not as automatic online learning.

The loop has three separate paths:

```text
Inference path:
  point-in-time inputs -> M01 -> M02 -> M03 -> M04 -> M05 -> M06 -> M07 -> M08 -> optional M09 -> M10

Evaluation path:
  fold/replay settles -> future labels, utilities, diagnostics, and residuals are joined after the fact

Promotion feedback path:
  evaluation evidence -> review/promotion gate -> later-fold artifact update or rejection
```

No future label, realized utility, downstream failure, broker outcome, same-fold Layer 10 discovery, or post-event interpretation may feed back into the same fold's inference features. A layer can learn from failure only through a later training/evaluation dataset, frozen artifact lineage, and accepted review gate.

Layer 10 has one special feedback route:

```text
Layer 5/6/7/8/9 replay failure
  -> Layer 10 residual event attribution
  -> reviewed event-family or strategy-failure packet
  -> future Layer 4 candidate training/evaluation
  -> future-fold Layer 4 acceptance only after review
```

Layer 10 must not become a generic hindsight corrector. It owns residual event attribution, intervention utility, and future Layer 4 packet eligibility only. Non-event model misses remain the evaluation/promotion evidence of their owning layer.

Layer 4 consumes accepted Layer 10 focus-pool event contracts as frozen qualitative/time-parameter inputs. Layer 10 owns event-family identity, point-in-time clocks, scope, visibility, selected impact windows, allowed use, and later demotion/split/reweight/parameter revision. Layer 4 owns only the quantitative conditional response and failure-risk mapping inside that frozen contract. It may output event-conditioned response strength, direction tendency, uncertainty, failure risk, path risk, entry/cap/disable pressure, and evidence/applicability confidence; it must not output standalone event alpha or change Layer 10 event parameters. Layer 5 remains the first layer that converts Layer 4 event-conditioned response/risk features into adjusted after-cost alpha.

Layer 5 event-conditioned alpha contrasts may use accepted Layer 10-to-Layer 4 focus-pool rows to test whether frozen Layer 4 event-conditioning features add after-cost signal versus a no-Layer-4 baseline. Same-fold focus-pool contrasts are diagnostic only; promotion still requires the full Layer 5 route with complete point-in-time Layer 1/2/3/4 features, leakage controls, split stability, and promotion review.

| Layer | Inference dependency | Primary output | Label / utility source after fold close | Feedback owner | Forbidden feedback |
|---|---|---|---|---|---|
| `M01` Market Regime | Broad-market and cross-asset point-in-time features. | `market_context_state` | Future broad-market state, volatility, liquidity, transition, and downstream calibration-lift labels. | Layer 1 evaluation and promotion evidence. | Sector/security choices, strategy/action labels, portfolio outcomes, and future market labels as same-fold inputs. |
| `M02` Sector Context | `market_context_state` plus ETF/sector behavior features. | `context_etf_state` and handoff evidence. | Future sector trend/tradability, handoff quality, and downstream candidate-lift labels. | Layer 2 evaluation and promotion evidence. | Static holdings as fitted shortcut, final target labels, alpha labels, future sector rank, and downstream target outcomes as same-fold inputs. |
| `M03` Target State | Layer 1/2 context plus anonymous target-local features and candidate policy. | `target_context_state` and candidate ranking evidence. | Future target path, persistence/reversion, liquidity/tradability, state-transition, and candidate-ranking labels. | Layer 3 evaluation and promotion evidence. | Raw ticker/company identity, alpha/action labels, future selected-target outcomes, and downstream trade results as same-fold inputs. |
| `M04` Event Failure Risk | Layer 1/2/3 state plus reviewed event-family or strategy-failure evidence and frozen Layer 10 focus-pool event contracts. | `event_failure_risk_vector` | Reviewed event-conditioned response, uncertainty, strategy-failure, entry-block, exposure-cap, disable, path-risk, and session-gap labels. | Layer 4 evaluation and event-strategy promotion review; contract-stress diagnostics route back to Layer 10. | Raw news/provider text, unreviewed event candidates, same-fold Layer 10 residual attribution, standalone event-alpha labels, Layer 10 event-parameter mutation, and future realized impact labels as same-fold inputs. |
| `M05` Alpha Confidence | Layer 1/2/3 state plus Layer 4 conditioning and quality/calibration evidence. | `alpha_confidence_vector` | After-cost alpha, residual return, path quality, reversal/drawdown, reliability, and calibration labels. | Layer 5 evaluation and promotion evidence. | Account/position/action/execution state, future returns, future event revisions, and Layer 10 promotion packets as same-fold inputs. |
| `M06` Dynamic Risk Policy | Global market/event pressure, Layer 5 alpha summary, and replay-safe portfolio/risk context. | `dynamic_risk_policy_state` | Portfolio/risk-budget utility, drawdown, CVaR, turnover, cost, and policy-stability labels. | Layer 6 off-policy evaluation and promotion evidence. | Broker/account mutation, target-specific identity distortion, order/fill outcomes as inference features, and hard-limit overrides. |
| `M07` Position Projection | Layer 5 alpha, Layer 6 policy, current/pending exposure, cost, friction, and price-location context. | `position_projection_vector` | Candidate exposure utility, regret, turnover, drawdown, budget-breach, and hold/flat comparison labels. | Layer 7 evaluation and promotion evidence. | Historical action labels, final order quantities, broker fills, alpha relearning, and execution instructions as same-fold inputs. |
| `M08` Underlying Action | Layer 7 projection, Layer 5 alpha, exposure state, quote/liquidity/borrow, and risk policy context. | `underlying_action_plan` / `underlying_action_vector` | Candidate action utility, no-trade/maintain calibration, entry/risk-plan quality, fill-realism, churn, and path labels. | Layer 8 evaluation and promotion evidence. | Broker order fields, option contract choice, historical action imitation, raw selected-action PnL, and execution leakage. |
| `M09` Option Expression | Completed Layer 8 thesis plus option-surface status, timestamped option candidates, and option exposure context. | `trading_guidance_record`, `option_expression_plan`, and `expression_vector` when optionable. | Candidate expression utility, realistic option after-cost return, fill/slippage/theta/IV, underlying-only labels for evaluated option surfaces, and no-option status labels for unavailable routes. | Layer 9 option replay evaluation and promotion evidence. | Best-contract hindsight, future option paths, realized fills, broker order ids, final quantities, and same-fold Layer 10 discoveries. |
| `M10` Event Risk Governor | Layer 1-9 thesis context plus point-in-time event observations, scope mapping, and residual-event evidence. | `event_risk_intervention` / `event_context_vector` plus future packet eligibility. | Residual intervention utility, attribution correctness, tail-failure reduction, overblock cost, and event-family packet labels. | Layer 10 residual evaluation, event-family review, and future Layer 4 packet routing. | Same-fold upstream feature mutation, automatic Layer 4 promotion, standalone event alpha, broker/account mutation, and generic non-event model correction. |

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

## Layer Designs

| Layer | Role | Target / utility | Canonical model family | Deterministic remains | Validation gate |
|---|---|---|---|---|---|
| `M01` Market Regime | Conditional state estimator | Broad-market latent state distributions: volatility regime, trend persistence, liquidity stress, correlation crowding, dispersion opportunity, and transition risk. | Temporal-feature LightGBM GBDT state estimator with quantile/ordinal outputs where labels support them. | Point-in-time scalers, feature eligibility, timestamp enforcement, coverage/freshness gates, schema. | Walk-forward evidence that market state improves Layer 2, Layer 5, and Layer 6 calibration or drawdown control versus a market-context-free baseline. |
| `M02` Sector Context | Conditional cross-sectional estimator | ETF/sector tradability and rotation behavior conditioned on Layer 1: trend quality, relative persistence, reversal/chop risk, liquidity, and context-dependent bias. | LightGBM learning-to-rank / cross-sectional GBDT ranker with hierarchical sector pooling when coverage supports it. | Eligible ETF universe, point-in-time reference handling, liquidity hard exclusions, no hard-coded style labels. | Out-of-time improvement in downstream candidate quality and alpha calibration versus naive relative-strength and market-only baselines. |
| `M03` Target State | Anonymous target-state estimator | Conditional target path distribution, persistence/reversion pressure, liquidity/cost tradability, transition risk, and target-sector-market interaction. | Entity-anonymous panel GBDT with multi-horizon path and state-transition heads. | Candidate construction policy, identity stripping, point-in-time joins, duplicate handling, row-quality gates. | Broad historical generalization plus live-route simulation; must prove incremental value over Layer 1+2 and adversarial no-identity-leakage. |
| `M04` Event Failure Risk | Reviewed event-conditioned response estimator | Conditional response and failure-risk uplift from accepted event/strategy-failure families: response strength/direction/uncertainty, entry block, cap pressure, disable pressure, and path-risk amplifier. | Calibrated event-impact GBDT with family pooling and conformal risk bands where sample size supports them. | Accepted event-family registry, frozen Layer 10 event contract, review gate, scope mapping, point-in-time event availability. | Event-family holdout and matched-control tests plus downstream Layer 5 lift; must avoid failures without simply suppressing all trades and must not become standalone event alpha. |
| `M05` Alpha Confidence | Calibrated edge estimator | Direct normalized after-cost alpha score: `0.5` is after-cost neutral, above `0.5` is positive edge, below `0.5` is negative edge; companion outputs cover direction, reliability, and path risk. | Calibrated after-cost GBDT score regressor with multi-horizon bundle; add quantile/distributional heads once labels exist for path-risk intervals. | Label construction, cost model, fixed replay threshold at `0.5`, point-in-time feature assembly, no identity fitting. | Fixed-threshold after-cost replay utility, calibration around `0.5`, and monotonic realized edge by score bucket. |
| `M06` Dynamic Risk Policy | Portfolio policy optimizer | Portfolio/risk-budget policy from global market state, systemic event pressure, portfolio/account replay state, and optional candidate/position quality summaries. Objective is risk-adjusted portfolio utility versus deterministic baselines, not single-trade PnL or alpha rank. | Final-contract constrained policy: contextual bandit, conservative policy-improvement/OPE model, monotonic calibrated tree/GBM utility scorer, or stronger policy optimizer that preserves constraints and explainability. | Broker/account mutation exclusion, hard exposure caps, buying-power/account/regulatory limits, kill switches, and target-entanglement guards. | Off-policy evaluation and walk-forward portfolio replay proving drawdown/CVaR improvement, cost discipline, policy stability, scope isolation, target-permutation robustness, and no target-specific distortion of global budget. |
| `M07` Position Projection | Exposure utility optimizer | Constrained target-exposure state utility from final Layer 5 alpha summary, Layer 6 risk policy, current/pending exposure, cost/friction, portfolio/risk, and price-location context. Objective is candidate exposure utility and regret reduction, not PnL prediction or action choice. | Final-contract exposure utility learner: pairwise/listwise ranker, regret-minimizing utility model, calibrated utility regressor, monotonic constrained GBDT, or stronger optimizer that preserves constraints and explainability. | Current/pending position accounting, exposure definitions, hard max/min exposure, cost floors, Layer 6 policy gates, no-action-label guards, and alpha-relearn guards. | Position-level replay proves lower regret, better risk-adjusted utility, lower unnecessary churn, stable horizon resolution, action isolation, alpha isolation, and improvement versus current/flat/alpha-only/fixed-confidence/cost-blind/risk-blind baselines. |
| `M08` Underlying Action | Structured offline action-plan policy | Constrained utility over candidate offline direct-underlying action theses: open, increase, reduce, close, cover, maintain, no-trade, or bearish-path/no-short-allowed, plus entry, target, stop, time-stop, and Layer 9 handoff quality. Objective is candidate plan utility, not historical action imitation, raw PnL, order execution, or option selection. | Final-contract candidate-plan scorer/ranker: pairwise/listwise ranker, calibrated utility/risk multi-head model, constrained contextual policy evaluator, or stronger optimizer that preserves offline thesis boundaries, fill realism, and explainability. | Action vocabulary, broker/order-field exclusion, option-contract exclusion, quote/liquidity/borrow hard gates, conservative hypothetical fill rules, no-action-label guards, no-execution-leakage guards. | Walk-forward replay proves action utility, no-trade and maintain calibration, entry/risk-plan quality, churn reduction, fill realism, Layer 9 handoff usefulness, action isolation, execution isolation, and improvement versus no-trade/maintain/alpha-only/gap-only/deterministic baselines. |
| `M09` Option Expression | Offline expression utility optimizer | Constrained utility over candidate option expressions for the completed Layer 8 thesis: long call, long put, or underlying-only expression when an option universe is available; no-option expression is the unavailable/not-applicable status route. Objective is realistic after-cost expression utility, not alpha discovery, underlying-action choice, historical selected-contract imitation, raw selected-contract PnL, order execution, or broker approval. | Final-contract candidate-expression scorer/ranker: pairwise/listwise contract ranker, calibrated utility/risk multi-head model, constrained expected-utility optimizer, or distributional payoff simulator when point-in-time chain labels are mature and the same boundary is preserved. | Option eligibility, option-surface status, contract availability, spread/liquidity hard filters, conservative fill assumptions, allowed-structure policy, pending-option exposure accounting, no best-contract-hindsight guards, and no broker/order mutation. | Walk-forward chain replay proves after-cost utility, no-option and underlying-only calibration, fill realism, spread/liquidity/IV/theta stress robustness, chain coverage, target-identity robustness, and improvement versus no-option/underlying-only/ATM/fixed-delta/fixed-DTE/deterministic baselines. |
| `M10` Event Risk Governor | Residual event-risk governance and attribution | Constrained utility over candidate residual event interventions after Layers 1-9 have produced a thesis: maintain, warn, cap, block entry, reduce/flatten review, or request human review; also emits future Layer 4 review-packet eligibility. Objective is residual intervention utility and attribution confidence, not event alpha, directional return prediction, accepted Layer 4 scoring, action choice, option expression, sizing, or execution. | Final-contract residual intervention scorer/ranker: calibrated residual-risk classifier, constrained GBDT utility scorer, candidate-intervention ranker, multi-head attribution/packet-eligibility model, or anomaly detector only as a residual candidate generator. | Same-fold discovery quarantine, review workflow, hard known-event blocks, source/revision provenance, co-event/confounder grouping, residual non-overlap proof, stale-regime decay, overblock accounting, and broker/account mutation exclusion. | Walk-forward residual-intervention replay proves fewer tail failures and better risk-adjusted utility without excessive opportunity destruction; validates calibration, attribution scope, co-event dominance, family holdouts, stale-regime decay, identity/duplicate-feature leakage, and future Layer 4 packets only after review. |

## Redesign Risks

The main risk is target entanglement. Layers 5, 7, 8, and 9 can all accidentally learn "the trade that would have made money." Their boundaries must stay separate:

```text
Layer 5 estimates edge.
Layer 6 sets portfolio/risk policy.
Layer 7 projects desired exposure.
Layer 8 chooses the underlying action thesis.
Layer 9 chooses the expression.
```

Policy layers also require stronger validation than ordinary supervised models. Layers 6-9 must use walk-forward replay, off-policy evaluation where applicable, and sensitivity checks for costs, fills, turnover, and liquidity.

Layer 10 must not become a hindsight oracle. Residual discoveries from replay are attribution and future evidence, not same-fold upstream features.

## Minimal Implementation Gate

Before expanding a layer implementation, define its objective contract:

1. primary target or utility;
2. prediction horizon;
3. label construction and cost assumptions;
4. inputs allowed at `available_time`;
5. forbidden inputs;
6. baseline to beat;
7. walk-forward validation metric;
8. leakage test;
9. downstream consumer.

Then trace one historical fold row through Layers 1-10. Every emitted field must be classifiable as estimate, policy output, hard gate, diagnostic, explainability, or attribution. Any field that mixes score, policy, reason, and constraint should be split before implementation proceeds.
