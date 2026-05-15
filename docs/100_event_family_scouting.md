# Event Family Scouting

Status: active Layer 8 research/governance contract.

This document turns the option-abnormality proof work into a stricter route for event-risk modeling. It does **not** promote `event_activity_bridge` or raw option abnormality into a model layer.

## Purpose

Raw option abnormality and raw news proximity failed the current promotion standard. Matched controls weakened the standalone option-abnormality relationship, and simple Alpaca-news proximity was too broad to separate useful event-risk amplification from ordinary news saturation.

Future event-risk work must therefore scout coherent event families before training or promotion. The unit of study is not "all news" or "all option flow". The unit is an interpreted event family with point-in-time lifecycle clocks, materiality rules, canonical source precedence, and abnormal-activity bridge rules.

## Required `event_family_scouting_packet_v1`

Each event family must have a packet before model training or risk-intervention promotion work begins.

Required fields:

```text
event_family_key
family_status
family_definition
inclusion_criteria
exclusion_criteria
canonical_source_precedence
lifecycle_class_default
required_event_clocks
required_interpretation_fields
materiality_rules
surprise_or_known_status_rules
scope_routing_defaults
narrative_residual_rules
abnormal_activity_bridge_rules
control_design
forward_label_design
minimum_coverage_gate
early_stop_criteria
review_required_triggers
accepted_examples
near_miss_examples
negative_examples
source_artifact_refs
study_artifact_refs
```

Accepted family status values:

```text
proposed
scouting
pilot_training
accepted_active
deferred_low_signal
retired_no_signal
review_required
```

## Promotion boundary

A family may enter `pilot_training` only after scouting evidence shows at least one stable, point-in-time relationship that survives controls.

A family must **not** enter `accepted_active` unless evidence includes:

- reviewed `event_interpretation_v1` artifacts or an accepted deterministic equivalent for the family;
- point-in-time clocks (`published_time`, `available_time`, `interpretation_time`, and family-specific clocks such as `scheduled_time` or `resolution_time` when applicable);
- materiality or surprise/known-status fields where relevant;
- matched controls that are not merely same-symbol price controls when event/non-event status matters;
- market/sector/base-feature controls where the family is expected to overlap with normal price/volume/liquidity state;
- split stability across dates, symbols, and at least one out-of-sample or holdout slice;
- no leakage from future event results, future article revisions, or future market reaction.

Raw event proximity alone is explicitly insufficient.

## Current scouting results

### Option abnormality alone

Artifact: `/root/projects/trading-model/storage/option_activity_matched_control_study_20260515/`

Result: current complete-evidence option abnormality did not prove a robust incremental relationship versus matched controls.

- `bullish_activity`: 10d path-range delta -0.10 percentage points; 10d directional delta -0.98 percentage points.
- `bearish_activity`: 10d path-range delta -0.34 percentage points; only a small +0.78 percentage-point directional delta.

Status: `deferred_low_signal` for standalone option abnormality.

### Strict option abnormality filters

Artifact: `/root/projects/trading-model/storage/option_activity_strict_filter_study_20260515/`

Result: intuitive strict filters did not rescue the relationship. Bullish filters became underpowered and generally underperformed controls. Bearish filters sometimes improved directional deltas but were small and still weak on path expansion.

Status: `deferred_low_signal` for threshold-only option abnormality refinement.

### Raw news proximity as amplifier

Artifact: `/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/`

Result: raw Alpaca-news proximity was too broad. 147/152 abnormal windows had prior/same-day PIT news, so "near news" could not separate signal from ordinary news saturation. Overall PIT-news-proximate windows had roughly flat/negative matched-control deltas.

Status: `deferred_low_signal` for raw option abnormality + raw news proximity.

### Earnings/guidance family candidate

The first promising family slice is `earnings_or_guidance_news` from the event-risk amplifier diagnostic:

- 20 windows;
- 4 symbols;
- 10d absolute-return delta about +3.08 percentage points versus controls;
- 10d path-range delta about +1.47 percentage points versus controls.

This is not enough for promotion. It is enough to justify `scouting` status for a dedicated earnings/guidance event-family packet.

The dedicated packet is `docs/101_earnings_guidance_event_family_packet.md`.

Required next evidence for this family:

- canonical earnings calendar / report source precedence rather than headline-only detection;
- scheduled-known/outcome-later lifecycle split between pre-event shell, release-result artifact, and post-event absorption;
- actual result and guidance interpretation only after release artifact visibility;
- surprise/magnitude fields when consensus or prior guidance is point-in-time available;
- option abnormality bridge relation typed as pre-event precursor, co-event reaction, or post-event absorption;
- verified non-event and non-earnings controls;
- verified no-option-abnormality controls before any earnings+option abnormality amplifier claim;
- split stability across more dates, expiries, and symbols.

Latest control update: `/root/projects/trading-model/storage/same_symbol_non_earnings_option_control_verification_20260515/` changed the blocked earnings-control search to same-symbol non-earnings option windows and still found zero verified no sampled option-abnormality controls across 24 candidates. This strengthens the block on option-abnormality amplifier promotion under the current high-emission option-event standard.

Status: `scouting`.

## Early-stop criteria

Stop or downgrade a family to `deferred_low_signal` or `retired_no_signal` when any of these hold after a bounded scout:

- event interpretation coverage is too sparse or mostly low confidence;
- controls erase the apparent edge;
- effect is concentrated in one symbol/date/story;
- direction/path effect flips across small reasonable specification changes;
- event timing cannot be represented point-in-time without leakage;
- the family mostly duplicates base model features rather than adding residual event-risk information.

## Non-goals

This contract does not authorize:

- a new model layer;
- direct buy/sell/hold decisions;
- broker or account mutation;
- option contract selection;
- treating news sentiment as alpha;
- treating post-event realized price moves as inference-time event facts.

## Final event-layer judgment link

The current go/no-go judgment is `docs/102_event_layer_final_judgment.md`.

Event-family scouting remains the required path. The event layer is accepted structurally as a risk/intelligence overlay, but no event family currently has enough controlled evidence for active alpha promotion. Option abnormality, strict option filters, and raw-news proximity remain `deferred_low_signal`; earnings/guidance remains `scouting` after the canonical shell/control pass.
