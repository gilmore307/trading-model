# State Vector Feature Semantics Registry
<!-- ACTIVE_LAYER_REORDER_NOTICE -->
> Active architecture revision (2026-05-15): conceptual Layers 4-8 are now Layer 4 AlphaConfidenceModel, Layer 5 PositionProjectionModel, Layer 6 UnderlyingActionModel, Layer 7 TradingGuidanceModel / OptionExpressionModel, and Layer 8 EventRiskGovernor / EventIntelligenceOverlay. Active physical implementation paths are aligned to the current conceptual numbering, including `model_08_event_risk_governor` and `model_07_option_expression`.
<!-- /ACTIVE_LAYER_REORDER_NOTICE -->


Status: Accepted semantics guardrail for Layer 1/2/3 state-vector fields, Layer 8 event-risk score families, Layer 4 alpha-confidence score families, Layer 5 position-projection score families, conceptual Layer 6 underlying-action score families, and conceptual Layer 7 option-expression score families.

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

## Layer 8 event-risk-context score semantics

Layer 8 `event_context_vector` / event-risk intervention values must keep these axes separate:

```text
event presence != event intensity
event intensity != impact scope
impact scope != direction
direction bias != alpha
event risk != trade action
```

Accepted event-context scalar score values currently retain the legacy `4_` prefix and `<horizon>` suffix for horizon-aware families until a dedicated score-token migration is accepted. Enum-like audit fields may share the horizon suffix in model-local contracts, but they are not `state_vector_value` registry rows.

Core risk/quality families:

- `8_event_presence_score_<horizon>` — `[0, 1]`, event presence, not good/bad by itself.
- `8_event_timing_proximity_score_<horizon>` — `[0, 1]`, closer to a sensitive event window.
- `8_event_intensity_score_<horizon>` — `[0, 1]`, stronger information shock/attention.
- `8_event_direction_bias_score_<horizon>` — `[-1, 1]`, target-conditioned positive/negative event bias; not alpha confidence.
- `8_event_context_alignment_score_<horizon>` — `[-1, 1]`, event supports/conflicts with current `target_context_state`.
- `8_event_uncertainty_score_<horizon>` — `[0, 1]`, high-is-bad information uncertainty.
- `8_event_gap_risk_score_<horizon>` — `[0, 1]`, high-is-bad jump/gap risk.
- `8_event_reversal_risk_score_<horizon>` — `[0, 1]`, high-is-bad current-path reversal risk.
- `8_event_liquidity_disruption_score_<horizon>` — `[0, 1]`, high-is-bad spread/depth/slippage disruption risk.
- `8_event_contagion_risk_score_<horizon>` — `[0, 1]`, high-is-bad cross-scope transmission risk.
- `8_event_context_quality_score_<horizon>` — `[0, 1]`, high-is-good evidence quality.

Impact-scope families:

- `8_event_market_impact_score_<horizon>`
- `8_event_sector_impact_score_<horizon>`
- `8_event_industry_impact_score_<horizon>`
- `8_event_theme_factor_impact_score_<horizon>`
- `8_event_peer_group_impact_score_<horizon>`
- `8_event_symbol_impact_score_<horizon>`
- `8_event_microstructure_impact_score_<horizon>`
- `8_event_scope_confidence_score_<horizon>`
- `8_event_scope_escalation_risk_score_<horizon>`
- `8_event_target_relevance_score_<horizon>`

Model-local audit/debug field:

- `8_event_dominant_impact_scope_<horizon>` — enum/routing/audit family; not a scalar score registry value; use carefully as model evidence and prefer numeric scope scores when fitting.

## Layer 4 alpha-confidence score semantics

Conceptual Layer 4 `alpha_confidence_vector` values must keep these axes separate:

```text
target direction evidence != alpha confidence
event direction bias != base alpha prerequisite
confidence != expected residual return
expected residual return != target exposure
risk != no-trade instruction
alpha confidence != option expression
alpha confidence != final action
```

Accepted alpha-confidence score values still use the legacy `5_` prefix and `<horizon>` suffix for horizon-aware families until a dedicated physical rename. Action/routing fields, position sizing, account-risk allocations, option-contract choices, and final verdicts are not `state_vector_value` rows for conceptual Layer 4.

Core final adjusted alpha-confidence families:

- `4_alpha_direction_score_<horizon>` — `[-1, 1]`, signed long/short alpha direction; not a buy/sell/hold action.
- `4_alpha_strength_score_<horizon>` — `[0, 1]`, absolute alpha strength regardless of direction sign.
- `4_expected_return_score_<horizon>` — `[-1, 1]`, standardized residual expected return after market/sector baseline adjustment.
- `4_alpha_confidence_score_<horizon>` — `[0, 1]`, model confidence in the alpha judgment.
- `4_signal_reliability_score_<horizon>` — `[0, 1]`, historical out-of-sample reliability for similar signals.
- `4_path_quality_score_<horizon>` — `[0, 1]`, high-is-good expected path smoothness/tradability.
- `4_reversal_risk_score_<horizon>` — `[0, 1]`, high-is-bad risk that the alpha direction is interrupted or reversed.
- `4_drawdown_risk_score_<horizon>` — `[0, 1]`, high-is-bad adverse excursion / MAE / drawdown risk.
- `4_alpha_tradability_score_<horizon>` — `[0, 1]`, alpha-level suitability for Layer 6 position projection; not a target exposure, position gap, or operation.

Base/unadjusted `5_base_*` fields are legacy-prefix diagnostics for Layer 1/2/3-only attribution and are not registered as core conceptual Layer 5-facing `state_vector_value` rows.

## Layer 5 position-projection score semantics

Conceptual Layer 5 `position_projection_vector` values must keep these axes separate:

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

Accepted position-projection score values still use the legacy `6_` prefix and `<horizon>` suffix for horizon-aware families until a dedicated physical rename. Buy/sell/hold/open/close/reverse, instrument selection, option-chain fields, strike/DTE/Greeks, order routing, and execution outputs are not `state_vector_value` rows for conceptual Layer 5.

Core final position-projection families:

- `5_target_position_bias_score_<horizon>` — `[-1, 1]`, signed target holding-direction bias; not a buy/sell/hold operation.
- `5_target_exposure_score_<horizon>` — `[-1, 1]`, normalized abstract target risk exposure; not shares, contracts, or order quantity.
- `5_current_position_alignment_score_<horizon>` — `[0, 1]`, high-is-good alignment between current plus pending exposure and projected target state.
- `5_position_gap_score_<horizon>` — `[-1, 1]`, target exposure minus effective current exposure; not an execution instruction.
- `5_position_gap_magnitude_score_<horizon>` — `[0, 1]`, absolute normalized target-current exposure gap; not urgency by itself.
- `5_expected_position_utility_score_<horizon>` — `[-1, 1]`, expected risk-adjusted net utility of the projected target holding state.
- `5_cost_to_adjust_position_score_<horizon>` — `[0, 1]`, high-is-bad relative cost pressure to close the position gap.
- `5_risk_budget_fit_score_<horizon>` — `[0, 1]`, high-is-good compatibility with current risk budget and portfolio constraints.
- `5_position_state_stability_score_<horizon>` — `[0, 1]`, high-is-good stability of the projected target holding state across alpha, horizon, cost, risk, and pending-order uncertainty.
- `5_projection_confidence_score_<horizon>` — `[0, 1]`, confidence in the Layer 6 alpha-to-position mapping; separate from Layer 5 alpha confidence.

## Layer 6 underlying-action score semantics

Conceptual Layer 6 `underlying_action_plan` and `underlying_action_vector` values must keep these axes separate:

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

Accepted underlying-action score families still use the legacy `7_` prefix and `<horizon>` suffix for horizon-aware families until a dedicated physical rename. Planned action types, resolved handoff fields, reason codes, entry/target/stop prices, quantities, and conceptual Layer 7 trading-guidance handoff fields are plan payload fields, not broker-order fields.

Core legacy `7_` underlying-action score families:

- `6_underlying_trade_eligibility_score_<horizon>` — `[0, 1]`, high-is-good direct-underlying trade eligibility after hard/soft gates.
- `6_underlying_action_direction_score_<horizon>` — `[-1, 1]`, signed direct-underlying planned side; positive long-side, negative short-side, near zero maintain/no-trade.
- `6_underlying_trade_intensity_score_<horizon>` — `[0, 1]`, high-is-more planned adjustment intensity after confidence, risk, cost, stability, and liquidity compression.
- `6_underlying_entry_quality_score_<horizon>` — `[0, 1]`, high-is-good planned entry quality.
- `6_underlying_expected_return_score_<horizon>` — `[-1, 1]`, signed favorable direct-underlying return quality.
- `6_underlying_adverse_risk_score_<horizon>` — `[0, 1]`, high-is-bad adverse move / stop-risk pressure.
- `6_underlying_reward_risk_score_<horizon>` — `[0, 1]`, high-is-good reward/risk quality.
- `6_underlying_liquidity_fit_score_<horizon>` — `[0, 1]`, high-is-good direct-underlying liquidity/spread fit.
- `6_underlying_holding_time_fit_score_<horizon>` — `[0, 1]`, high-is-good compatibility between planned holding time and horizon/path evidence.
- `6_underlying_action_confidence_score_<horizon>` — `[0, 1]`, calibrated confidence in the offline direct-underlying action thesis.

Model-local plan/handoff fields include `6_resolved_underlying_action_type`, `6_resolved_action_side`, `6_resolved_dominant_horizon`, `6_resolved_trade_eligibility_score`, `6_resolved_trade_intensity_score`, `6_resolved_entry_quality_score`, `6_resolved_action_confidence_score`, and `6_resolved_reason_codes`. They summarize the plan and do not send orders.

## Layer 7 option-expression score semantics

Conceptual Layer 7 `option_expression_plan` and `expression_vector` values must keep these axes separate:

```text
underlying action plan != option expression
option expression != broker order
contract_ref != broker order id
selected_contract != send order
contract constraints != route / time-in-force
premium risk plan != account mutation
expression confidence != final approval
Layer 8 offline plan != live execution
```

Accepted Layer 8 score families use the `8_` prefix and `<horizon>` suffix for horizon-aware scalar scores. Selected contract refs, contract constraints, premium-risk plan fields, and reason codes are plan payload fields, not broker-order fields.

Core Layer 8 score families:

- `7_option_expression_eligibility_score_<horizon>` — `[0, 1]`, high-is-good option-expression admissibility.
- `7_option_expression_direction_score_<horizon>` — `[-1, 1]`, signed expression direction; positive call-side/bullish, negative put-side/bearish, near zero no-option expression.
- `7_option_contract_fit_score_<horizon>` — `[0, 1]`, high-is-good selected contract fit.
- `7_option_liquidity_fit_score_<horizon>` — `[0, 1]`, high-is-good option spread/volume/open-interest fit.
- `7_option_iv_fit_score_<horizon>` — `[0, 1]`, high-is-good IV/IV-rank fit.
- `7_option_greek_fit_score_<horizon>` — `[0, 1]`, high-is-good delta/Greek fit.
- `7_option_reward_risk_score_<horizon>` — `[0, 1]`, high-is-good premium reward/risk quality.
- `7_option_theta_risk_score_<horizon>` — `[0, 1]`, high-is-bad theta-decay pressure.
- `7_option_fill_quality_score_<horizon>` — `[0, 1]`, high-is-good conservative fill-quality estimate.
- `7_option_expression_confidence_score_<horizon>` — `[0, 1]`, calibrated confidence in the offline option-expression plan.

Model-local resolved fields include `7_resolved_expression_type`, `7_resolved_option_right`, `7_resolved_dominant_horizon`, `7_resolved_selected_contract_ref`, `7_resolved_contract_fit_score`, `7_resolved_expression_confidence_score`, `7_resolved_no_option_reason_codes`, and `7_resolved_reason_codes`. They summarize the selected expression and do not send orders.
