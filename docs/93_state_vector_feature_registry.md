# State Vector Feature Semantics Registry
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-17): conceptual Layers 4-9 are now Layer 4 EventFailureRiskModel, Layer 5 AlphaConfidenceModel, Layer 6 PositionProjectionModel, Layer 7 UnderlyingActionModel, Layer 8 TradingGuidanceModel / OptionExpressionModel, and Layer 9 EventRiskGovernor / EventIntelligenceOverlay. Physical implementation paths for Layers 4-9 remain on prior numbering until a dedicated code/SQL renumbering migration.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: Accepted semantics guardrail for Layer 1/2/3 state-vector fields, Layer 4 event-failure-risk score families, Layer 5 alpha-confidence score families, Layer 6 position-projection score families, Layer 7 underlying-action score families, Layer 8 trading-guidance/option-expression score families, and Layer 9 event-risk score families.

This registry prevents the state/context/action-vector system from mixing direction, quality, risk, scope, routing, diagnostics, plan fields, execution fields, and research-only payloads.

Canonical implementation:

```text
src/models/state_vector_feature_registry.py
```

## Required semantic classes

- Direction fields are signed `[-1, 1]`: positive/negative indicate state direction only.
- Direction-strength fields are `[0, 1]`: high can describe either long or short evidence.
- Quality/tradability fields are `[0, 1]` high-is-good and direction-neutral unless explicitly named signed alignment.
- Risk/noise/exhaustion fields are `[0, 1]` high-is-bad.
- Liquidity fields must say whether high means pressure/bad or support/good.
- Routing fields (`eligibility`, `handoff`, `rank`, reason codes) are not ordinary model evidence.
- Diagnostics (`coverage`, `data_quality`, `state_quality`, evidence counts) govern trust/gating, not alpha.
- Research-only fields (`target_state_embedding`, `state_cluster_id`) must not replace inspectable blocks or be promoted without walk-forward fit/assign controls.

## Layer 2 correction

`2_sector_dispersion_crowding_score` is retired from the active primary contract because dispersion and crowding are not the same state. The active split is:

- `2_sector_internal_dispersion_score` — internal fragmentation/dispersion, high-is-bad for clean handoff context.
- `2_sector_crowding_risk_score` — one-factor/crowding/co-movement pressure, high-is-bad.

## Layer 3 tradability validation

`3_tradability_score_<window>` must be validated against path and execution outcomes, not only forward return:

- MFE/MAE balance;
- path efficiency;
- first target-before-stop style path behavior when stop/target policies are reviewed;
- direction flip count;
- state-transition rate;
- spread/liquidity degradation.

Stable short states can score highly when direction strength, trend quality, path stability, context support, liquidity, persistence, and quality are strong while noise, transition risk, and exhaustion risk are low.

## Layer 4 event-failure-risk score semantics

Conceptual Layer 4 `event_failure_risk_vector` values must keep these axes separate:

```text
event/strategy-failure evidence != raw news
event failure risk != standalone directional alpha
entry-block pressure != broker order instruction
exposure-cap pressure != final position size
strategy-disable pressure != account mutation
evidence quality != event presence
applicability confidence != causal proof
```

Core conceptual Layer 4 score families use `4_event_*` names and require a reviewed evidence packet plus explicit agent/manager acceptance before production use. No local screen may auto-promote a family into Layer 4.

## Layer 5 alpha-confidence score semantics

Conceptual Layer 5 `alpha_confidence_vector` values must keep these axes separate:

```text
target direction evidence != alpha confidence
event_failure_risk_vector != standalone event alpha
confidence != expected residual return
expected residual return != target exposure
risk != no-trade instruction
alpha confidence != option expression
alpha confidence != final action
```

Current physical alpha-confidence score values may still use legacy `4_*` prefixes until a dedicated physical rename. Action/routing fields, position sizing, account-risk allocations, option-contract choices, and final verdicts are not `state_vector_value` rows for conceptual Layer 5.

## Layer 6 position-projection score semantics

Conceptual Layer 6 `position_projection_vector` values must keep these axes separate:

```text
alpha confidence != target exposure
target position bias != buy/sell
target exposure != order quantity
position gap != execution instruction
position gap magnitude != urgency
cost to adjust position != no-trade action
risk budget fit != final approval
projection confidence != alpha confidence
position projection vector != final action
```

Current physical position-projection score values may still use legacy `5_*` prefixes until a dedicated physical rename. Buy/sell/hold/open/close/reverse, instrument selection, option-chain fields, strike/DTE/Greeks, order routing, and execution outputs are not `state_vector_value` rows for conceptual Layer 6.

## Layer 7 underlying-action score semantics

Conceptual Layer 7 `underlying_action_plan` and `underlying_action_vector` values must keep these axes separate:

```text
alpha confidence != planned underlying action
position gap != trade instruction
target exposure != planned quantity
planned quantity != broker order quantity
trade eligibility != final approval
entry plan != order type
stop_loss_price != broker stop order
take_profit_price != broker limit order
underlying price-path thesis != guaranteed outcome
underlying action plan != option expression
underlying action plan != live execution
```

Current physical underlying-action score families may still use legacy `6_*` prefixes until a dedicated physical rename. Planned action types, resolved handoff fields, reason codes, entry/target/stop prices, quantities, and conceptual Layer 8 trading-guidance handoff fields are plan payload fields, not broker-order fields.

## Layer 8 trading-guidance / option-expression score semantics

Conceptual Layer 8 `trading_guidance_record`, `option_expression_plan`, and `expression_vector` values must keep these axes separate:

```text
underlying action plan != trading approval
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 8 offline plan != live execution
```

Current physical option-expression score families may still use legacy `7_*` prefixes until a dedicated physical rename. Selected contract refs, contract constraints, premium-risk plan fields, and reason codes are plan payload fields, not broker-order fields.

## Layer 9 event-risk-context score semantics

Conceptual Layer 9 `event_context_vector` / `event_risk_intervention` values must keep these axes separate:

```text
event presence != event intensity
event intensity != impact scope
impact scope != direction
direction bias != alpha
event risk != trade action
residual explanation != causal proof
observation-pool addition != Layer 4 promotion
```

Current physical event-context scalar score values may still use legacy `8_*` prefixes until a dedicated score-token migration is accepted. Enum-like audit fields may share the horizon suffix in model-local contracts, but they are not `state_vector_value` registry rows. Layer 9 may emit warning/cap/block/review/flatten-candidate overlays and Layer 4 promotion packets, but it must not send orders or mutate accounts.
