# Model Framework Readiness

Status: accepted framework-selection assessment
Date: 2026-06-10

## Principle

The current six-model stack should not make PyTorch or any deep-learning framework a default dependency.

Framework choice is downstream of objective contracts, point-in-time datasets, labels, leakage tests, walk-forward splits, calibration, baseline comparison, and trading-utility evidence. A model may use a neural framework only after a specific model surface proves that learned sequence or representation structure is necessary and beats simpler baselines after costs and calibration.

## Default Ladder

Use the weakest model class that clears the promotion evidence bar:

1. deterministic pilot and rules as reference behavior;
2. simple statistical baselines;
3. regularized linear or logistic models;
4. tree-based models such as LightGBM, XGBoost, CatBoost, random forests, or calibrated gradient boosting;
5. conservative ensembles after individual behavior is understood;
6. PyTorch or similar neural models only behind explicit neural-readiness gates.

Deep learning is not a shortcut around missing data contracts or promotion evidence.

## Readiness Matrix

| Model | Current recommended class | PyTorch readiness | Neural trigger |
|---|---|---|---|
| `M01 BackgroundContextModel` | deterministic reference, regularized regression/classification, tree boosting | not ready | Large point-in-time cross-asset/sector sequences show stable regime representation lift beyond tree baselines. |
| `M02 TargetStateModel` | ranking baselines, regularized models, tree boosting, calibrated rank/utility models | not ready | Large anonymous target panel with stable temporal/cross-sectional interaction lift that survives walk-forward and identity-leakage tests. |
| `M03 EventStateModel` | reviewed event features, calibrated event response/risk models, tree boosting | possible later | Accepted event text/filing/news embeddings or event trajectories materially improve event-conditioned response/risk over reviewed structured-event baselines. |
| `M04 UnifiedDecisionModel` | cost-aware utility model, calibrated tree/linear baselines, constrained policy scoring | possible later | Sequence/state fusion beats strong M01-M03 plus cost/risk baselines on after-cost decision utility, no-trade calibration, and regime stability. |
| `M05 OptionExpressionModel` | option-chain filters, calibrated utility/ranking models, tree boosting | not ready | Large option-chain replay shows learned surface/term-structure representation improves fill/cost/theta/IV-adjusted utility over transparent candidate ranking. |
| `M06 ResidualEventGovernanceModel` | deterministic guardrails, calibrated residual-risk/overblock models, event attribution baselines | possible later | Residual event trajectories or text-derived representations reduce missed-event loss without excessive overblock cost across walk-forward regimes. |

## Neural-Readiness Gates

A model surface may introduce PyTorch only when all of these are true:

- The objective contract is complete: target or utility, horizon, labels/costs, allowed inputs, forbidden inputs, baseline, metric, leakage test, and downstream consumer.
- The point-in-time dataset is large enough for the proposed neural architecture without fragile overfit.
- The proposed neural input is not a disguised future label, same-fold downstream outcome, raw identity leak, or unreviewed event artifact.
- A strong non-deep baseline has already been implemented and evaluated.
- The neural candidate beats the baseline on walk-forward splits after transaction costs, liquidity/fill realism, and calibration.
- Performance is stable across regimes and not concentrated in one market window.
- Diagnostics and explanations are sufficient for promotion review and failure analysis.
- The model still emits the same current contract output; framework choice must not create a new public contract.

## Current Decision

PyTorch is out of scope for the current implementation lane. The next accepted work is:

- build the M01-M06 full-chain local runner and evidence receipt;
- assemble real point-in-time datasets and labels;
- implement transparent baselines for each model;
- evaluate baseline lift, leakage, calibration, stability, and after-cost utility;
- revisit neural models only for surfaces whose evidence shows a specific representation or sequence advantage.

If a future neural candidate is justified, it should enter as an implementation backend for the existing model contract, not as a new model layer or compatibility route.
