# Cumulative Model Framework Readiness

Status: accepted single-scheme cumulative-learning route
Date: 2026-06-28

## Principle

The current six-model stack uses one learned model scheme:

`continual_residual_mlp`

This is a replayable cumulative neural residual-learning family over point-in-time state vectors. It is target-anonymous but not target-blind: raw ticker, company, security id, ISIN, CUSIP, and equivalent identity fields are forbidden model inputs, while legitimate state differences such as liquidity, volatility, spread, optionability, sector context, and market regime remain valid features.

The route is selected for cumulative data absorption, future online deployment, and one shared lifecycle contract. It is not selected because the first small validation receipt proved promotion readiness. Promotion still requires layer-specific labels, walk-forward replay, calibration, cost/fill stress, leakage checks, checkpoint replay, rollback evidence, and full-chain utility evidence.

## Single Scheme

All learned M01-M06 surfaces use the same model family and lifecycle:

- model scheme: `continual_residual_mlp`
- current lightweight implementation: `one_hidden_layer_mlp_sgd`
- future implementation evolution: deeper or residual MLP internals only when they preserve the same public scheme, checkpoint, replay, and output contracts
- forbidden active alternatives: online-linear, FTRL, passive-aggressive, tree boosting, parallel challenger models, sequence models, embedding models, factorization models, and state-space models as separate active schemes

Deterministic behavior remains valid for hard guardrails, schema validation, routing, reference behavior, and safety checks. It must not become a second learned-model route.

## Layer Mapping

| Layer | Selected model role | Deciding metrics |
|---|---|---|
| `M01 BackgroundContextModel` | Continual residual MLP market, sector, liquidity, volatility, and transition-state estimator. | Calibration, regime-transition accuracy, volatility/liquidity error, stability across regimes, downstream lift to M02-M04. |
| `M02 TargetStateModel` | Continual residual MLP anonymous target-state ranker/classifier with calibrated eligibility and utility scores. | Rank IC/NDCG, calibrated eligibility, persistence/reversion error, liquidity/tradability error, identity-leakage checks, downstream target-selection utility. |
| `M03 EventStateModel` | Continual residual MLP structured-event response/risk model over reviewed event features. | Event-bucket calibration, response/risk Brier or log loss, tail-risk recall at fixed false-block cost, stability by event family, no same-fold M06 leakage. |
| `M04 UnifiedDecisionModel` | Continual residual MLP cost-aware multi-head utility and constrained policy scorer. | After-cost utility, no-trade calibration, downside/path risk, turnover/churn, exposure regret, fill/cost sensitivity, chain-level PnL/risk improvement. |
| `M05 OptionExpressionModel` | Continual residual MLP option-vs-underlying utility/ranking model over timestamped option candidates. | Option after-cost utility, slippage/theta/IV-adjusted return, fill realism, top-k candidate ranking, no-option calibration, underlying-only counterfactual comparison. |
| `M06 ResidualEventGovernanceModel` | Continual residual MLP residual-risk and overblock-cost model with deterministic guardrails. | Missed-event loss reduction, overblock cost, attribution precision/recall, intervention utility, future-packet quality, strict quarantine from same-fold upstream mutation. |

Layer-specific heads, losses, masks, horizons, and output schemas are allowed. A different model family is not.

## Lifecycle Contract

Every learned model checkpoint must include:

- feature schema and feature-map hash;
- point-in-time scaler, normalizer, and calibration state;
- weights and optimizer/update state needed to continue cumulative training;
- training data manifest, including symbol scope, time scope, label maturity clock, and excluded future windows;
- update cadence and replay clock;
- checkpoint id, parent checkpoint id, and rollback path;
- target-anonymity checks;
- calibration metrics and threshold-near decision diagnostics.

The model must support:

- `predict(as_of_time, state_vector, checkpoint)`;
- `update(as_of_time, finalized_training_events)`;
- `checkpoint(as_of_time)`;
- `restore(checkpoint_id)`;
- deterministic replay over a fixed manifest.

## Storage Policy

The scheme should not require indefinite raw artifact retention. Long-term retention should prefer compact canonical feature-label streams, checkpoint manifests, source provenance, and enough immutable evidence to reproduce accepted training updates. Raw provider artifacts may be compacted or deleted under the repository storage lifecycle policy after canonical feature-label rows and provenance are verified.

## Acceptance Gates

The selected scheme must pass these gates before any promotion:

- checkpoint restore reproduces predictions;
- weights, scalers, normalizers, feature maps, calibration state, and update state are checkpointed;
- no future labels, raw identity, same-fold downstream outcomes, or M06 hindsight feedback enter inference;
- surrogate identity dominance is diagnosed and understood;
- walk-forward improvement holds across folds, symbols, and regimes;
- probabilities and utilities are calibrated near decision thresholds;
- M04 and M05 survive transaction-cost, slippage, liquidity, fill, and turnover stress;
- implementation changes do not change public layer output contracts;
- layer improvement is downstream-neutral or downstream-positive under chain replay.

## Current Evidence

The first small cumulative model scheme validation used AAPL, MSFT, and NVDA over 2016-01 through 2016-06 with 3,600 examples and 3,575 labeled rows. It proved that the current lightweight MLP implementation can train, checkpoint, restore, and emit bounded predictions under the target-anonymous source-proxy harness.

The result is evidence to continue implementing `continual_residual_mlp`. It is not model promotion evidence.
