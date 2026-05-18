# Promotion Acceptance
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-17): Layers 1-9 are MarketRegimeModel, SectorContextModel, TargetStateVectorModel, EventFailureRiskModel, AlphaConfidenceModel, PositionProjectionModel, UnderlyingActionModel, TradingGuidanceModel / OptionExpressionModel, and EventRiskGovernor / EventIntelligenceOverlay. Active physical implementation paths use the current Layer 4-9 numbering; historical/applied migration records may retain prior numbering.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: accepted current production-promotion evidence receipt; no production activation
Date: 2026-05-09

## Summary

No model layer is production-promoted by this acceptance evidence.

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
| 4 | `model_04_event_failure_risk` | missing EventFailureRiskModel evaluation substrate / calibrated strategy-failure labels | deferred: no production eval substrate | none |
| 5 | `model_05_alpha_confidence` | missing production adjusted-alpha eval run / calibrated labels | deferred: no production eval substrate | none |
| 6 | `model_06_position_projection` | missing production position-utility eval run / labels | deferred: no production eval substrate | none |
| 7 | `model_07_underlying_action` | missing production realized-action outcome eval run | deferred: no production eval substrate | none |
| 8 | `model_08_option_expression` | missing production option-chain replay eval run | deferred: no production eval substrate | none |
| 9 | `model_09_event_risk_governor` | missing residual-event-governor eval run / calibrated residual-risk labels | deferred: no production eval substrate | none |

## Layer 1 and 2 evidence

Layer 1 and Layer 2 have real database evidence paths. The current evidence is useful negative evidence, not promotion approval:

- Layer 1 data completeness/leakage classification is now explicit: missing model rows at label decision times are alignment/completeness evidence, not future leakage. No-future-leak and chronological split-overlap checks pass, but promotion is still blocked by model-row count, eval-label count, model/label alignment, pair-count, coverage, correlation, baseline-improvement, and split-stability gates.
- Layer 2 uses the same leakage/alignment separation. No-future-leak and chronological split-overlap checks pass, but promotion is still blocked by model/label alignment, coverage/pair-count, baseline, stability, and sector handoff gates.

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

The acceptance helper `scripts/models/review_layers_03_08_promotion_acceptance.py` builds blocked model-side evidence and reviewer artifacts for the base Layers 3-8 surfaces. Its name is a bounded base-stack review scope, not a Layer 9 event-risk-governor activation path. It must not persist manager decisions or activate configs.

## Activation invariant

No production config is active from this acceptance pass. Deferred reviews must not create activation records or move active config pointers. Any durable activation record is manager-control-plane work in `trading-manager`.
