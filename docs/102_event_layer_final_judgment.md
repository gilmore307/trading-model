# Event Layer Final Judgment

Status: accepted judgment after the 2026-05-15 abnormal-activity, option-direction, matched-control, raw-news, and canonical earnings/guidance scouting passes.

## Decision

The event layer is worth building, but only as a bounded **EventRiskGovernor / EventIntelligenceOverlay**.

It is **not** currently worth promoting as a broad alpha layer, a standalone `EventActivityBridgeModel`, or an option-flow alpha model.

The correct route is:

```text
base model stack guidance
+ point-in-time canonical event evidence
+ interpreted event-family packets when accepted
+ abnormal-activity bridge evidence as provenance/risk context
  -> EventRiskGovernor / EventIntelligenceOverlay
  -> event risk intervention, uncertainty, review/block/cap/flatten hints
```

The layer should govern risk, uncertainty, lifecycle timing, canonical-event identity, and event/activity evidence quality. It should not choose entries, size positions, select option contracts, send orders, or override the base model stack with unproven event alpha.

## Why this is the right boundary

### 1. Standalone option abnormality did not clear controls

Artifacts:

- `/root/projects/trading-model/storage/option_activity_matched_control_study_20260515/`
- `/root/projects/trading-model/storage/option_activity_strict_filter_study_20260515/`

Complete-evidence option activity looked directionally interesting before controls, especially bullish activity. After matched controls, the current abnormality definition did not prove robust incremental path or directional value. Strict OI/IV/underlying/term/skew filters did not rescue it.

Conclusion: option abnormality is useful evidence/provenance, but not a promoted alpha input under the current definition.

### 2. Raw news proximity was too broad

Artifact: `/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/`

Raw PIT news appeared near almost every abnormal option window, so news proximity could not separate meaningful event risk from ordinary news saturation. Broad headline-keyword families are not a valid promotion route.

Conclusion: event work must be family-specific and canonical-source-led.

### 3. Earnings/guidance is promising but underpowered

Artifacts:

- `/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/`
- `/root/projects/trading-model/storage/earnings_guidance_event_scouting_20260515/`

The initial headline-keyword earnings/guidance slice was positive but small. The canonical Nasdaq-calendar control pass improved evidence quality, but produced only 9 abnormal windows on canonical earnings-shell dates across 2 symbols. Those windows showed positive 5d absolute-return and path-range deltas, but lacked enough coverage for 10d/14d stability or promotion.

Conclusion: earnings/guidance deserves continued scouting, not pilot training or activation yet.

## Accepted architecture

Build the event layer around four responsibilities:

1. **Canonical event timeline** — lifecycle class, clocks, shell/result split, point-in-time availability, dedup/canonical refs.
2. **Event interpretation** — reviewed `event_interpretation_v1` or deterministic family-equivalent rows for accepted event families.
3. **Event/activity bridge** — typed relationships such as pre-event precursor, co-event reaction, post-event absorption, divergence, and unresolved latent hazard.
4. **Risk-governor output** — uncertainty, gap/reversal/liquidity/contagion risk, human-review requirements, entry blocks, exposure caps, reduce/flatten candidates, and audit explanations.

## Rejected architecture

Do **not** build these as active model routes now:

- broad news sentiment alpha;
- raw news-proximity amplifier;
- standalone option abnormality alpha;
- threshold-only option-flow model;
- `EventActivityBridgeModel` as a separate promoted layer;
- event layer that directly emits buy/sell/hold, contract choice, order type, or account mutation.

## Promotion policy

The event layer may exist structurally as risk governance before alpha proof, but each event family must remain gated.

An event family may move from `scouting` to `pilot_training` only after it has:

- canonical source precedence and lifecycle clocks;
- result/interpretation fields only after point-in-time visibility;
- matched event/non-event controls;
- verified no-option-abnormality controls when option abnormality is part of the claim;
- forward labels that separate direction-neutral path expansion from directional alpha;
- split stability across symbols, sectors/themes, dates, and seasons;
- leakage review for future filings, revisions, and market reactions.

Until then, event evidence can support review/risk context, not promoted trading alpha.

## Current family statuses

| Family / route | Status | Judgment |
|---|---|---|
| Standalone option abnormality | `deferred_low_signal` | Diagnostic/provenance only. |
| Strict option abnormality refinement | `deferred_low_signal` | Threshold filters did not rescue controls. |
| Raw option abnormality + raw news proximity | `deferred_low_signal` | News proximity saturated; not separable. |
| Earnings/guidance | `scouting` | Worth continued canonical-source scouting; not promotion-ready. |
| EventRiskGovernor structural layer | `accepted_architecture` | Worth building as bounded risk/intelligence overlay. |

## Next build sequence

1. Keep the EventRiskGovernor structure and registry contracts.
2. Expand earnings/guidance evidence across more seasons and symbols.
3. Add official SEC/company result/guidance interpretation artifacts.
4. Verify no-option-abnormality controls by querying option-event feeds for control dates.
5. Re-run family-specific proof with direction-neutral path labels first and directional labels second.
6. Only then consider `pilot_training` for the family; do not promote broad event alpha.
