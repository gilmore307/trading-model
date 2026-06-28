# Cumulative Model Framework Readiness

Status: accepted per-layer single-scheme cumulative-learning route
Date: 2026-06-28

## Principle

The current six-model stack selects learned model schemes per layer. Each layer has exactly one active cumulative/replayable scheme at a time, and different layers may use different model families when their objectives, inputs, labels, replay constraints, and operational risks differ.

The route is selected for cumulative data absorption, future online deployment, and auditable model-state replay. It is not selected because one early validation receipt proves promotion readiness. Promotion still requires layer-specific labels, walk-forward replay, calibration, cost/fill stress, leakage checks, checkpoint replay, rollback evidence, and full-chain utility evidence.

Target-anonymous does not mean target-blind: raw ticker, company, security id, ISIN, CUSIP, and equivalent identity fields are forbidden model inputs, while legitimate state differences such as liquidity, volatility, spread, optionability, sector context, and market regime remain valid features.

## Per-Layer Single Active Scheme

The accepted contract is:

- one active learned scheme per layer;
- no parallel challenger route inside a layer;
- layers may choose different cumulative/replayable model families;
- an offline replacement study may exist only as evidence, not runtime routing;
- when a layer changes scheme, the old active scheme for that layer must be retired in the same acceptance batch.

A layer-selected scheme may evolve internally only when it preserves that layer's public output contract, checkpoint/restore contract, replay semantics, and rollback path. If the replacement changes model family or public behavior, it is a layer scheme replacement, not an implementation tweak.

Deterministic behavior remains valid for hard guardrails, schema validation, routing, reference behavior, and safety checks. It must not become a second learned-model route.

## Layer Selection Matrix

| Layer | Selection boundary | Current allowed decision shape | Deciding metrics |
|---|---|---|---|
| `M01 BackgroundContextModel` | Market, sector, liquidity, volatility, and regime state. | One cumulative/replayable context-state scheme selected by M01 evidence. | Calibration, regime-transition accuracy, volatility/liquidity error, stability across regimes, downstream lift to M02-M04. |
| `M02 TargetStateModel` | Anonymous target-state ranking, eligibility, and utility. | One cumulative/replayable target-state scheme selected by M02 evidence. | Rank IC/NDCG, calibrated eligibility, persistence/reversion error, liquidity/tradability error, identity-leakage checks, downstream target-selection utility. |
| `M03 EventStateModel` | Structured event response and risk. | One cumulative/replayable event-state scheme selected by M03 evidence. | Event-bucket calibration, response/risk Brier or log loss, tail-risk recall at fixed false-block cost, stability by event family, no same-fold M06 leakage. |
| `M04 UnifiedDecisionModel` | Cost-aware utility, action, no-trade, exposure, and policy scoring. | One cumulative/replayable decision-policy scheme selected by M04 evidence. | After-cost utility, no-trade calibration, downside/path risk, turnover/churn, exposure regret, fill/cost sensitivity, chain-level PnL/risk improvement. |
| `M05 OptionExpressionModel` | Option-vs-underlying expression and option candidate ranking. | One cumulative/replayable option-expression scheme selected by M05 evidence. | Option after-cost utility, slippage/theta/IV-adjusted return, fill realism, top-k candidate ranking, no-option calibration, underlying-only counterfactual comparison. |
| `M06 ResidualEventGovernanceModel` | Residual event risk, intervention, and overblock cost. | One cumulative/replayable residual-governance scheme selected by M06 evidence plus deterministic guardrails. | Missed-event loss reduction, overblock cost, attribution precision/recall, intervention utility, future-packet quality, strict quarantine from same-fold upstream mutation. |

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

The result is evidence that `continual_residual_mlp` is a viable layer scheme where its assumptions fit. It is not a global mandate for all six layers and not model promotion evidence.
