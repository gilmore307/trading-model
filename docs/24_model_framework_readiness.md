# Cumulative Model Framework Readiness

Status: accepted per-layer single-scheme cumulative-learning route
Date: 2026-06-28

## Principle

The current six-model stack selects learned model schemes per layer. Each layer has exactly one active cumulative/replayable scheme at a time. The accepted first active family is cumulative residual MLP, specialized per layer by head, loss, labels, and output contract.

The route is selected for cumulative data absorption, future online deployment, and auditable model-state replay. It is not selected because one early validation receipt proves promotion readiness. Promotion still requires layer-specific labels, walk-forward replay, calibration, cost/fill stress, leakage checks, checkpoint replay, rollback evidence, and full-chain utility evidence.

Target-anonymous does not mean target-blind: raw ticker, company, security id, ISIN, CUSIP, and equivalent identity fields are forbidden model inputs, while legitimate state differences such as liquidity, volatility, spread, optionability, sector context, and market regime remain valid features.

## Per-Layer Active Schemes

The accepted contract is:

- one active learned scheme per layer;
- no parallel challenger route inside a layer;
- layers use the active cumulative residual MLP family with layer-specific heads and losses;
- an offline replacement study may exist only as evidence, not runtime routing;
- when a layer changes scheme, the old active scheme for that layer must be retired in the same acceptance batch.

A layer-selected scheme may evolve internally only when it preserves that layer's public output contract, checkpoint/restore contract, replay semantics, and rollback path. If the replacement changes model family or public behavior, it is a layer scheme replacement, not an implementation tweak.

Deterministic behavior remains valid for hard guardrails, schema validation, routing, reference behavior, and safety checks. It must not become a second learned-model route.

## Active Layer Scheme Matrix

| Layer | Active learned scheme | Structure | Deciding metrics |
|---|---|---|---|
| `M01 BackgroundContextModel` | `continual_residual_mlp_context_classifier` | Hashed-feature residual MLP classifier/embedding model over point-in-time market, sector, liquidity, volatility, macro, and cross-asset state. | Calibration, regime-transition accuracy, volatility/liquidity error, stability across regimes, downstream lift to M02-M04. |
| `M02 TargetStateModel` | `continual_residual_mlp_target_ranker` | Pairwise/listwise residual MLP ranker over anonymous target-state vectors; no raw symbol identity. | Rank IC/NDCG, calibrated eligibility, persistence/reversion error, liquidity/tradability error, identity-leakage checks, downstream target-selection utility. |
| `M03 EventStateModel` | `continual_residual_mlp_event_risk_scorer` | Multi-head residual MLP event-risk scorer over reviewed structured event features, with direction, magnitude, horizon, and uncertainty heads. | Event-bucket calibration, response/risk Brier or log loss, tail-risk recall at fixed false-block cost, stability by event family, no same-fold M06 leakage. |
| `M04 UnifiedDecisionModel` | `continual_residual_mlp_policy_value` | Conservative supervised/off-policy residual MLP policy-value model over M01-M03 state, cost, risk, exposure, portfolio context, and no-trade context. | After-cost utility, no-trade calibration, downside/path risk, turnover/churn, exposure regret, fill/cost sensitivity, chain-level PnL/risk improvement. |
| `M05 OptionExpressionModel` | `continual_residual_mlp_option_chain_ranker` | Residual MLP option-chain ranker over option-relative features, Greeks, liquidity, spread, surface, horizon, and expression-state vectors. | Option after-cost utility, slippage/theta/IV-adjusted return, fill realism, top-k candidate ranking, no-option calibration, underlying-only counterfactual comparison. |
| `M06 ResidualEventGovernanceModel` | `continual_residual_mlp_risk_gate` | Calibrated residual MLP risk-gate/intervention scorer with abstain, block, size-down, and allow outputs plus deterministic hard guardrails. | Missed-event loss reduction, overblock cost, attribution precision/recall, intervention utility, future-packet quality, strict quarantine from same-fold upstream mutation. |

These are active scheme choices, not promotion claims. The current implementation can start with dependency-light `one_hidden_layer_mlp_sgd` where needed, but the accepted layer schemes are the structures above.

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

Every layer-selected model must support:

- `predict(as_of_time, state_vector, checkpoint)`;
- `update(as_of_time, finalized_training_events)`;
- `checkpoint(as_of_time)`;
- `restore(checkpoint_id)`;
- deterministic replay over a fixed manifest.

## Storage Policy

The route should not require indefinite raw artifact retention. Long-term retention should prefer compact canonical feature-label streams, checkpoint manifests, source provenance, and enough immutable evidence to reproduce accepted training updates. Raw provider artifacts may be compacted or deleted under the repository storage lifecycle policy after canonical feature-label rows and provenance are verified.

## Acceptance Gates

A layer-selected scheme must pass these gates before promotion:

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

The first small cumulative model scheme validation used AAPL, MSFT, and NVDA over 2016-01 through 2016-06 with 3,600 examples and 3,575 labeled rows. It proved that the lightweight `continual_residual_mlp` implementation can train, checkpoint, restore, and emit bounded predictions under the target-anonymous source-proxy harness.

The result is evidence that cumulative residual MLP checkpoints are viable. It does not by itself promote any layer. The active per-layer schemes are fixed by the matrix above and still need their layer-specific labels, replay, and promotion evidence.
