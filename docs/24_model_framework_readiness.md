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
