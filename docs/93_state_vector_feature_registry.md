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
confidence != expected value
expected value != target exposure
risk != no-trade instruction
alpha confidence != option expression
alpha confidence != final action
```

Accepted Layer 5 scalar alpha-confidence score values use the `5_` prefix and `<horizon>` suffix for horizon-aware families. Action/routing fields, position sizing, account-risk allocations, option-contract choices, and final verdicts are not `state_vector_value` rows for Layer 5.

Core alpha-confidence families:

- `5_alpha_direction_confidence_score_<horizon>` — `[-1, 1]`, calibrated long/short alpha confidence; not a buy/sell/hold action.
- `5_alpha_direction_strength_score_<horizon>` — `[0, 1]`, absolute confidence strength regardless of direction sign.
- `5_alpha_expected_return_score_<horizon>` — signed normalized forward-return expectation before trading projection.
- `5_alpha_expected_value_score_<horizon>` — signed normalized risk/uncertainty-adjusted alpha value before account-specific costs, expression, and sizing.
- `5_alpha_downside_risk_score_<horizon>` — `[0, 1]`, high-is-bad adverse path/loss risk.
- `5_alpha_tail_risk_score_<horizon>` — `[0, 1]`, high-is-bad extreme adverse outcome risk.
- `5_alpha_path_stability_score_<horizon>` — `[0, 1]`, high-is-good expected path smoothness/tradability.
- `5_alpha_uncertainty_score_<horizon>` — `[0, 1]`, high-is-bad confidence unreliability.
- `5_alpha_context_support_score_<horizon>` — `[0, 1]`, high-is-good market/sector/target/event support coherence.
- `5_alpha_event_adjustment_score_<horizon>` — `[-1, 1]`, event-driven positive/negative confidence adjustment relative to no-event baseline.
- `5_alpha_calibration_quality_score_<horizon>` — `[0, 1]`, high-is-good reliability/calibration quality for this context/horizon.
