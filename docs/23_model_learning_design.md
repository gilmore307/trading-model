# Model Learning Design

Status: accepted long-term learning route; implementation remains evidence-gated
Owner intent: each layer must have one clear role before its implementation is expanded.

## Core Principle

Each layer must do exactly one of these jobs:

- estimate a point-in-time conditional distribution or calibrated score;
- optimize a declared utility or policy under constraints;
- enforce deterministic hard constraints, accounting, timestamps, schemas, and safety gates;
- produce post-hoc attribution or future evidence packets.

A layer must not mix prediction, policy, hard enforcement, and attribution in the same score. Deterministic code may own contracts, feature assembly, timestamps, schemas, safety gates, and validation checks. It must not preserve an alternate scoring route for a layer whose current contract is trained estimation or policy optimization.

## Cross-Layer Rules

- Model-facing inputs must be point-in-time at `available_time`.
- Labels and outcomes are training/evaluation-only and must never enter inference vectors.
- Real ticker/company identity remains audit/routing metadata, not a fitting feature.
- Stable identity surrogates must be tested, not only banned by column name.
- Score thresholds should not hide model weakness. Where a score has a natural neutral point, training should produce that score directly.
- Layer 10 same-fold discoveries are quarantined from same-fold upstream training. Accepted discoveries may become future Layer 4 inputs only after evidence packet review.
- Validation must beat a realistic baseline, not just show historical fit.

## Layer Designs

| Layer | Role | Target / utility | Model family candidates | Deterministic remains | Validation gate |
|---|---|---|---|---|---|
| `M01` Market Regime | Conditional state estimator | Broad-market latent state distributions: volatility regime, trend persistence, liquidity stress, correlation crowding, dispersion opportunity, and transition risk. | Dynamic factor model, state-space model, HMM/HSMM, temporal gradient boosting, quantile/ordinal model, calibrated regime ensemble. | Point-in-time scalers, feature eligibility, timestamp enforcement, coverage/freshness gates, schema, cold-start reducer. | Walk-forward evidence that market state improves Layer 2, Layer 5, and Layer 6 calibration or drawdown control versus a market-context-free baseline. |
| `M02` Sector Context | Conditional cross-sectional estimator | ETF/sector tradability and rotation behavior conditioned on Layer 1: trend quality, relative persistence, reversal/chop risk, liquidity, and context-dependent bias. | Cross-sectional ranker, panel GBM, hierarchical Bayesian sector model, temporal attention/TCN, multi-task ETF/basket model. | Eligible ETF universe, point-in-time reference handling, liquidity hard exclusions, no hard-coded style labels. | Out-of-time improvement in downstream candidate quality and alpha calibration versus naive relative-strength and market-only baselines. |
| `M03` Target State | Anonymous target-state estimator | Conditional target path distribution, persistence/reversion pressure, liquidity/cost tradability, transition risk, and target-sector-market interaction. | Entity-anonymous panel model, GBM/TabNet, inspectable representation learning, temporal CNN/Transformer, survival/state-transition model. | Candidate construction policy, identity stripping, point-in-time joins, duplicate handling, row-quality gates. | Broad historical generalization plus live-route simulation; must prove incremental value over Layer 1+2 and adversarial no-identity-leakage. |
| `M04` Event Failure Risk | Reviewed event-risk estimator | Conditional failure-risk uplift from accepted event/strategy-failure families: entry block, cap pressure, disable pressure, and path-risk amplifier. | Calibrated classifier/regressor, uplift/causal model, hierarchical event-family model, Bayesian partial pooling, conformal risk classifier. | Accepted event-family registry, review gate, scope mapping, point-in-time event availability, conservative cold-start defaults. | Event-family holdout and matched-control tests; must avoid failures without simply suppressing all trades. |
| `M05` Alpha Confidence | Calibrated edge estimator | Direct normalized after-cost alpha score: `0.5` is after-cost neutral, above `0.5` is positive edge, below `0.5` is negative edge; companion outputs cover direction, reliability, and path risk. | Calibrated probabilistic return model, quantile regression, distributional GBM, conformal predictor, multi-horizon ensemble, pairwise/ranking auxiliary loss. | Label construction, cost model, fixed replay threshold at `0.5`, point-in-time feature assembly, no identity fitting. | Fixed-threshold after-cost replay utility, calibration around `0.5`, and monotonic realized edge by score bucket. |
| `M06` Dynamic Risk Policy | Portfolio policy optimizer | Portfolio/risk-budget policy from alpha distribution, market stress, portfolio exposure, capacity, and drawdown state. Objective is portfolio utility, not prediction alone. | Contextual bandit, offline constrained RL, model-predictive control, stochastic optimizer, hard-constrained policy network, utility-calibrated GBM. | Broker/account mutation exclusion, hard exposure caps, buying-power/account/regulatory limits, kill switches. | Off-policy evaluation and walk-forward portfolio replay proving drawdown/CVaR improvement, cost discipline, and no target-specific distortion of global budget. |
| `M07` Position Projection | Exposure utility optimizer | Desired abstract holding state and target exposure maximizing expected utility net of adjustment cost and risk-budget fit. | Constrained optimizer, utility regression, cost-aware policy model, monotone GBM, quadratic/stochastic portfolio optimizer. | Current/pending position accounting, exposure definitions, hard max/min exposure, cost floors, policy gates. | Position-level replay beats naive proportional sizing and current-position inertia baselines while controlling churn. |
| `M08` Underlying Action | Structured action policy | Offline underlying thesis: open, increase, reduce, close, maintain, or no-trade plus entry, stop, target, and time-stop policy. | Structured decision model, constrained optimizer over action templates, imitation model from replay decisions, survival/time-to-invalidity model, contextual policy model. | Action vocabulary, broker-field exclusion, quote sanity checks, price tick constraints, no-trade hard gates. | Action replay improves after-cost utility and reduces bad adjustments versus direct exposure-gap heuristics. |
| `M09` Option Expression | Expression utility optimizer | Whether and how to express the thesis with options under chain, liquidity, IV, Greek, fill, and premium-risk constraints. | Contract ranker, constrained optimizer, distributional payoff simulator, Bayesian expected-utility model, contextual expression policy. | Option eligibility, contract availability, spread/liquidity hard filters, conservative fill assumptions, allowed-structure policy, no broker mutation. | Chain-level point-in-time replay beats underlying-only and no-option baselines after realistic fills and slippage. |
| `M10` Event Risk Governor | Residual risk intervention and attribution | Post-thesis residual event-risk intervention: maintain, block, cap, reduce/flatten-review, or request review; also emits future Layer 4 discovery packets. | Calibrated residual-risk classifier, anomaly/event severity model, rules-plus-model ensemble, causal/uplift model for intervention benefit. | Same-fold discovery quarantine, review workflow, hard known-event blocks, source provenance, broker/account mutation exclusion. | Intervention replay avoids tail failures without excessive opportunity destruction; discovery packets affect only future folds after review. |

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
