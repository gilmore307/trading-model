# State Vector Feature Semantics Registry

Status: Accepted semantics guardrail for Layer 1/2/3 state-vector fields, Layer 4 event-context score families, and Layer 5 alpha-confidence score families.

This registry prevents the state/context-vector system from mixing direction, quality, risk, scope, routing, diagnostics, and research-only payloads.

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

## Layer 4 event-context score semantics

Layer 4 `event_context_vector` values must keep these axes separate:

```text
event presence != event intensity
event intensity != impact scope
impact scope != direction
direction bias != alpha
event risk != trade action
```

Accepted Layer 4 scalar event-context score values use the `4_` prefix and `<horizon>` suffix for horizon-aware families. Enum-like audit fields may share the horizon suffix in model-local contracts, but they are not `state_vector_value` registry rows.

Core risk/quality families:

- `4_event_presence_score_<horizon>` — `[0, 1]`, event presence, not good/bad by itself.
- `4_event_timing_proximity_score_<horizon>` — `[0, 1]`, closer to a sensitive event window.
- `4_event_intensity_score_<horizon>` — `[0, 1]`, stronger information shock/attention.
- `4_event_direction_bias_score_<horizon>` — `[-1, 1]`, target-conditioned positive/negative event bias; not alpha confidence.
- `4_event_context_alignment_score_<horizon>` — `[-1, 1]`, event supports/conflicts with current `target_context_state`.
- `4_event_uncertainty_score_<horizon>` — `[0, 1]`, high-is-bad information uncertainty.
- `4_event_gap_risk_score_<horizon>` — `[0, 1]`, high-is-bad jump/gap risk.
- `4_event_reversal_risk_score_<horizon>` — `[0, 1]`, high-is-bad current-path reversal risk.
- `4_event_liquidity_disruption_score_<horizon>` — `[0, 1]`, high-is-bad spread/depth/slippage disruption risk.
- `4_event_contagion_risk_score_<horizon>` — `[0, 1]`, high-is-bad cross-scope transmission risk.
- `4_event_context_quality_score_<horizon>` — `[0, 1]`, high-is-good evidence quality.

Impact-scope families:

- `4_event_market_impact_score_<horizon>`
- `4_event_sector_impact_score_<horizon>`
- `4_event_industry_impact_score_<horizon>`
- `4_event_theme_factor_impact_score_<horizon>`
- `4_event_peer_group_impact_score_<horizon>`
- `4_event_symbol_impact_score_<horizon>`
- `4_event_microstructure_impact_score_<horizon>`
- `4_event_scope_confidence_score_<horizon>`
- `4_event_scope_escalation_risk_score_<horizon>`
- `4_event_target_relevance_score_<horizon>`

Model-local audit/debug field:

- `4_event_dominant_impact_scope_<horizon>` — enum/routing/audit family; not a scalar score registry value; use carefully as model evidence and prefer numeric scope scores when fitting.

## Layer 5 alpha-confidence score semantics

Layer 5 `alpha_confidence_vector` values must keep these axes separate:

```text
target direction evidence != alpha confidence
event direction bias != alpha confidence
confidence != expected residual return
expected residual return != target exposure
risk != no-trade instruction
alpha confidence != option expression
alpha confidence != final action
```

Accepted Layer 5 scalar alpha-confidence score values use the `5_` prefix and `<horizon>` suffix for horizon-aware families. Action/routing fields, position sizing, account-risk allocations, option-contract choices, and final verdicts are not `state_vector_value` rows for Layer 5.

Core final adjusted alpha-confidence families:

- `5_alpha_direction_score_<horizon>` — `[-1, 1]`, signed long/short alpha direction; not a buy/sell/hold action.
- `5_alpha_strength_score_<horizon>` — `[0, 1]`, absolute alpha strength regardless of direction sign.
- `5_expected_return_score_<horizon>` — `[-1, 1]`, standardized residual expected return after market/sector baseline adjustment.
- `5_alpha_confidence_score_<horizon>` — `[0, 1]`, model confidence in the alpha judgment.
- `5_signal_reliability_score_<horizon>` — `[0, 1]`, historical out-of-sample reliability for similar signals.
- `5_path_quality_score_<horizon>` — `[0, 1]`, high-is-good expected path smoothness/tradability.
- `5_reversal_risk_score_<horizon>` — `[0, 1]`, high-is-bad risk that the alpha direction is interrupted or reversed.
- `5_drawdown_risk_score_<horizon>` — `[0, 1]`, high-is-bad adverse excursion / MAE / drawdown risk.
- `5_alpha_tradability_score_<horizon>` — `[0, 1]`, alpha-level suitability for Layer 6 trading projection; not a trading signal.

Base/unadjusted `5_base_*` fields are diagnostics for Layer 1/2/3-only attribution and are not registered as core Layer 6-facing `state_vector_value` rows.
