# Cumulative Model Framework Readiness

Status: accepted cumulative-learning framework route
Date: 2026-06-27

## Principle

The current six-model stack should prioritize replayable cumulative learners over batch-only model families. Framework choice remains downstream of objective contracts, point-in-time datasets, labels, leakage tests, walk-forward splits, calibration, baseline comparison, and trading-utility evidence.

The default implementation lane uses dependency-light online and neural candidates first. Heavy neural frameworks may enter only when a specific model surface proves that learned sequence or representation structure is necessary and beats simpler cumulative baselines after costs and calibration.

## Default Ladder

Use the weakest cumulative model class that clears the promotion evidence bar:

1. deterministic pilot and rules as reference behavior;
2. simple statistical baselines;
3. replayable online linear, logistic, SGD, FTRL, or passive-aggressive models;
4. small MLP or residual MLP state-vector models;
5. sequence, embedding, factorization, or state-space models where the layer objective needs them;
6. conservative ensembles only after individual behavior is understood.

Neural learning is not a shortcut around missing data contracts or promotion evidence. Batch-only tree boosting is no longer an active framework target; any retained tree artifact is historical evidence, not a current default route.

## Readiness Matrix

| Model | Current recommended class | Heavy neural readiness | Neural trigger |
|---|---|---|---|
| `M01 BackgroundContextModel` | online regression/classification, regime-state cumulative learners | possible later | Large point-in-time cross-asset/sector sequences show stable regime representation lift beyond online baselines. |
| `M02 TargetStateModel` | anonymous target-state online ranking and calibrated utility models | possible later | Large anonymous target panel with stable temporal/cross-sectional interaction lift that survives walk-forward and identity-leakage tests. |
| `M03 EventStateModel` | reviewed event features plus cumulative event response/risk models | possible later | Accepted event text/filing/news embeddings or event trajectories materially improve event-conditioned response/risk over reviewed structured-event baselines. |
| `M04 UnifiedDecisionModel` | cost-aware online utility model and constrained policy scoring | possible later | Sequence/state fusion beats strong M01-M03 plus cost/risk baselines on after-cost decision utility, no-trade calibration, and regime stability. |
| `M05 OptionExpressionModel` | cumulative option utility/ranking model over timestamped option candidates | possible later | Large option-chain replay shows learned surface/term-structure representation improves fill/cost/theta/IV-adjusted utility over transparent candidate ranking. |
| `M06 ResidualEventGovernanceModel` | cumulative residual-risk/overblock model plus deterministic guardrails | possible later | Residual event trajectories or text-derived representations reduce missed-event loss without excessive overblock cost across walk-forward regimes. |

## Neural-Readiness Gates

A model surface may introduce a heavy neural framework only when all of these are true:

- The objective contract is complete: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, metric, leakage test, and downstream consumer.
- The point-in-time dataset is large enough for the proposed neural architecture without fragile overfit.
- The proposed neural input is not a disguised future label, same-fold downstream outcome, raw identity leak, or unreviewed event artifact.
- A strong cumulative baseline has already been implemented and evaluated.
- The neural candidate beats the baseline on walk-forward splits after transaction costs, liquidity/fill realism, and calibration.
- Performance is stable across regimes and not concentrated in one market window.
- Diagnostics and explanations are sufficient for promotion review and failure analysis.
- The model still emits the same current contract output; framework choice must not create a new public contract.

## Current Decision

The current implementation lane removes batch-only tree boosting from the active route. The accepted next work is:

- build the M01-M06 full-chain local runner and evidence receipt;
- assemble real point-in-time datasets and labels;
- implement replayable online/MLP cumulative candidates for each applicable model;
- evaluate lift, leakage, calibration, stability, checkpoint replay, rollback, and after-cost utility;
- introduce heavier neural models only for surfaces whose evidence shows a specific representation or sequence advantage.

If a future neural candidate is justified, it should enter as an implementation backend for the existing model contract, not as a new model layer or compatibility route.

## Final Experiment Contract

Backend selection is decided by layer-specific bake-offs under the shared cumulative-learning control contract in `docs/23_model_learning_design.md`. The decision is not a global model-family choice. Each layer must select the weakest replayable cumulative learner that clears its own objective, leakage, calibration, checkpoint, and downstream-chain utility gates.

Every candidate must produce two verdicts:

- `candidate_viable`: the backend can train, checkpoint, restore, replay deterministically, and pass leakage checks without changing the public layer contract.
- `promotion_ready`: the backend improves the layer metric and does not degrade the full M01-M06 chain under walk-forward replay evidence.

The final active route for experiments is:

| Layer | Primary candidate | Required challenger | Gated later candidate | Deciding metrics |
|---|---|---|---|---|
| `M01 BackgroundContextModel` | Online regression/classification for market, sector, liquidity, volatility, and transition state. | Small residual MLP over checkpointed state vectors. | Temporal/state-space regime learner only if sequence evidence beats online/MLP baselines. | Calibration, regime-transition accuracy, volatility/liquidity error, stability across regimes, downstream lift to M02-M04. |
| `M02 TargetStateModel` | Anonymous target-state online ranker/classifier with calibrated eligibility and utility scores. | Small residual MLP over anonymous target-state panel vectors. | Factorization, panel embedding, or listwise neural ranker only after identity-leakage probes pass. | Rank IC/NDCG, calibrated eligibility, persistence/reversion error, liquidity/tradability error, identity-leakage probe failure, downstream target-selection utility. |
| `M03 EventStateModel` | Structured-event online response/risk model over reviewed event features. | Residual MLP over accepted event-state vectors. | Event embedding, event trajectory, or text-derived representation only after reviewed event artifacts and leakage gates exist. | Event-bucket calibration, response/risk Brier or log loss, tail-risk recall at fixed false-block cost, stability by event family, no same-fold M06 leakage. |
| `M04 UnifiedDecisionModel` | Cost-aware multi-head online utility and constrained policy scorer. | Residual MLP over M01-M03 state, cost, risk, exposure, and portfolio context vectors. | Sequence/state-fusion policy scorer only if it improves after-cost utility and no-trade calibration across regimes. | After-cost utility, no-trade calibration, downside/path risk, turnover/churn, exposure regret, fill/cost sensitivity, chain-level PnL/risk improvement. |
| `M05 OptionExpressionModel` | Online option-vs-underlying utility/ranking model over timestamped option candidates. | Residual MLP over option-surface, liquidity, theta, IV, cost, and expression-state vectors. | Surface/term-structure representation model only after large option-chain replay shows stable lift. | Option after-cost utility, slippage/theta/IV-adjusted return, fill realism, top-k candidate ranking, no-option calibration, underlying-only counterfactual comparison. |
| `M06 ResidualEventGovernanceModel` | Online residual-risk and overblock-cost model with deterministic guardrails. | Residual MLP over residual event, thesis, intervention, and failure-context vectors. | Event trajectory or text representation only if it reduces missed-event loss without excessive overblock cost. | Missed-event loss reduction, overblock cost, attribution precision/recall, intervention utility, future-packet quality, strict quarantine from same-fold upstream mutation. |

The first implementation wave must include only dependency-light cumulative candidates:

- online linear/logistic/regression, SGD, FTRL, or passive-aggressive variants as the primary family;
- small MLP or residual MLP as the required nonlinear challenger;
- deterministic/rule behavior only as reference behavior and hard guardrails, not as a learned-model substitute.

Heavy neural, sequence, embedding, factorization, or state-space candidates are second-wave candidates. They may enter only after the primary online candidate and required MLP challenger produce clean evidence receipts and the layer shows a specific representation or temporal-structure gap.

## Experiment Sequence

Run the selection in this order:

1. **Replay contract proof.** Use a small multi-symbol, multi-fold harness to prove deterministic checkpoint restore, point-in-time scaler/normalizer state, feature-schema stability, raw and surrogate identity-leakage checks, and M06 same-fold quarantine. If this fails, no backend comparison is valid.
2. **Layer-local bake-off.** For each layer, train the primary online candidate and required MLP challenger on the same point-in-time state-vector stream, with the same labels, folds, masks, and applicability states.
3. **Chain replay.** Replay the full M01-M06 chain using each viable layer candidate while holding the other layers at their best viable current candidate. A layer-local win that damages downstream chain behavior is rejected.
4. **Stress slices.** Report all accepted candidates by regime, symbol group, sector/liquidity bucket, optionable/non-optionable state, event/no-event state, and high-volatility windows. Concentrated wins do not promote.
5. **Backend selection.** Pick the weakest candidate that is viable, stable, calibrated, replayable, and non-degrading downstream. Prefer online primary over MLP unless MLP produces stable material lift. Prefer MLP over heavier neural unless heavier neural proves a layer-specific representation advantage.

Required acceptance gates for every candidate:

- replay restore reproduces predictions;
- weights, scalers, normalizers, embeddings, feature maps, and calibration state are checkpointed;
- no future labels, raw identity, surrogate identity dominance, same-fold downstream outcomes, or M06 hindsight feedback enter inference;
- walk-forward improvement holds across folds, symbols, and regimes;
- probabilities and utilities are calibrated near decision thresholds;
- M04 and M05 survive transaction-cost, slippage, liquidity, fill, and turnover stress;
- backend changes do not change public layer output contracts;
- layer improvement is downstream-neutral or downstream-positive under chain replay.
