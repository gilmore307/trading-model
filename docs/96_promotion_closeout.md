# Promotion Closeout Evidence
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-17): conceptual Layers 4-9 are now Layer 4 EventFailureRiskModel, Layer 5 AlphaConfidenceModel, Layer 6 PositionProjectionModel, Layer 7 UnderlyingActionModel, Layer 8 TradingGuidanceModel / OptionExpressionModel, and Layer 9 EventRiskGovernor / EventIntelligenceOverlay. Physical implementation paths for Layers 4-9 remain on prior numbering until a dedicated code/SQL renumbering migration.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: accepted current production-promotion evidence receipt; no production activation
Date: 2026-05-09

## Summary

No model layer is production-promoted by this closeout evidence.

`trading-model` owns evidence generation and reviewer artifacts only:

- model outputs;
- labels;
- evaluation runs;
- promotion metrics;
- candidate evidence packages;
- reviewer artifacts.

Durable promotion requests, review decisions, activation, rollback, and production pointers belong in `trading-manager` through the unified `model_promotion_review` path.

## Current readiness receipt

| Layer | Model | Evidence state | Current status | Activation |
|---:|---|---|---|---|
| 1 | `model_01_market_regime` | real PostgreSQL evaluation evidence exists | deferred: baseline, label-count, pair-count, and coverage gates still fail | none |
| 2 | `model_02_sector_context` | real PostgreSQL evaluation evidence exists | deferred: baseline/lift/stability gates still fail | none |
| 3 | `model_03_target_state_vector` | real PostgreSQL production-eval substrate exists | deferred: upstream Layer 1/2 approvals and Layer 3 calibration evidence missing | none |
| 4 | `model_08_event_risk_governor` | missing production event-overlay eval run / calibrated labels | deferred: no production eval substrate | none |
| 5 | `model_04_alpha_confidence` | missing production adjusted-alpha eval run / calibrated labels | deferred: no production eval substrate | none |
| 6 | `model_05_position_projection` | missing production position-utility eval run / labels | deferred: no production eval substrate | none |
| 7 | `model_06_underlying_action` | missing production realized-action outcome eval run | deferred: no production eval substrate | none |
| 8 | `model_07_option_expression` | missing production option-chain replay eval run | deferred: no production eval substrate | none |

## Layer 1 and 2 evidence

Layer 1 and Layer 2 have real database evidence paths. The current evidence is useful negative evidence, not promotion approval:

- Layer 1 data completeness/leakage repair succeeded, and the current split-stability checks pass after excluding quality outputs from predictive-return factor scoring. Promotion is still blocked by baseline improvement (`-0.4488 < 0.0`), eval-label count (`72 < 200`), minimum pair count (`4 < 30`), and coverage (`0.20 < 0.80`).
- Layer 2 coverage improved, but baseline improvement, selected-vs-blocked lift, and split sign-stability gates still block promotion.

The model repo may regenerate these evidence packages, but durable review requests and decisions must be submitted through `trading-manager`.

## Layer 3 evidence

Layer 3 has a real production-evaluation substrate for `feature_03_target_state_vector` and generated `model_03_target_state_vector` rows. Its measured thresholds can be evaluated, but promotion remains deferred because:

- Layer 1 and Layer 2 are not production-approved active upstream dependencies;
- Layer 3 calibration evidence is missing.

## Layers 4-9 blockers

Layers 4-9 remain explicit blockers, not informal work items:

- Layer 4 requires a reviewed EventFailureRiskModel implementation/evaluation substrate for accepted event/strategy-failure conditioning.
- Layer 5 requires calibrated adjusted-alpha outcomes.
- Layer 6 requires position-utility/outcome labels.
- Layer 7 requires realized underlying-action outcome evaluation.
- Layer 8 requires option-chain replay and option-expression / base trading-guidance outcome evidence.
- Layer 9 requires real residual-event-risk labels and production evaluation metrics.

The legacy closeout helper `scripts/models/review_layers_03_08_promotion_closeout.py` builds blocked model-side evidence and reviewer artifacts for the physical Layers 3-8 surfaces. Until a dedicated renumbering migration exists, its name is a physical-path note, not the conceptual layer order. It must not persist manager decisions or activate configs.

## Activation invariant

No production config is active from this closeout pass. Deferred reviews must not create activation records or move active config pointers. Any durable activation record is manager-control-plane work in `trading-manager`.
