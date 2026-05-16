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

## First itemized test after judgment — earnings/guidance event-alone

Artifact: `/root/projects/trading-model/storage/earnings_guidance_event_alone_q4_2025_20260515/`

The first one-by-one follow-up test examined canonical earnings/guidance scheduled shells alone, before option abnormality or result interpretation.

Result: the Q4 2025 12-symbol slice showed positive direction-neutral path expansion versus same-symbol non-earnings controls: 5d path-range delta about +2.76 percentage points, 10d path-range delta about +2.17 percentage points, and 14d path-range delta about +1.23 percentage points. Directional return did not improve; 5d directional delta was about -1.69 percentage points.

Judgment update: earnings/guidance remains the strongest family to continue, but the useful relationship is currently path/risk/volatility expansion, not direction. Status remains `scouting` until official result/guidance interpretations and no-option-abnormality controls are added.

## Second itemized test — official result-artifact scout

Artifact: `/root/projects/trading-model/storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/`

The next follow-up joined the Q4 2025 earnings shells to official SEC submission/companyfacts artifacts. All 12 events had an official SEC result artifact in the event window; 11 had partial XBRL metric-direction interpretation, while guidance interpretation remained missing.

Judgment update: official SEC result artifacts strengthen the canonical event-family route, but simple reported-metric YoY direction is not enough for signed alpha. The event layer boundary remains risk/intelligence overlay first. Promotion still requires official guidance/result interpretation, consensus or accepted expectation baselines, verified option-abnormality controls, and family-specific stability evidence.

## Third itemized test — earnings plus option-abnormality split

Artifact: `/root/projects/trading-model/storage/earnings_option_abnormality_split_scout_20260515/`

The first earnings+option split check used only existing reviewed local artifacts. It found two option-covered canonical earnings rows, both with verified option abnormality, and zero verified earnings-without-option-abnormality controls.

Judgment update: the earnings+option amplifier claim is still blocked. The next evidence requirement is not another model-layer expansion; it is acquisition or verification of matched earnings dates with no option abnormality under the same option-event standard.

## Fourth itemized test — sampled no-option-abnormality controls

Artifact: `/root/projects/trading-model/storage/earnings_option_no_abnormality_control_probe_20260515/`

A bounded sampled-contract probe attempted to create earnings-without-option-abnormality controls for the canonical earnings set. It referenced 80 contract probes for the eight earnings rows not covered by the prior option matrix and found zero verified no sampled option-abnormality controls. Six newly probed earnings rows had verified option abnormality; two rows had partial contract coverage due ThetaData HTTP 472 but still emitted abnormality on successful sampled contracts.

Judgment update: the earnings+option amplifier comparison remains blocked, not positive or negative. Continuing this route requires either broader-chain no-abnormality verification that actually yields clean controls, or a different control design; the EventRiskGovernor boundary does not expand.

## Fifth itemized test — same-symbol non-earnings option controls

Artifact: `/root/projects/trading-model/storage/same_symbol_non_earnings_option_control_verification_20260515/`

After the earnings-date sampled probe found zero clean controls, the next route changed control design: same-symbol non-earnings candidate windows from the existing local option matrix, excluding dates within ±3 calendar days of a same-symbol Nasdaq earnings shell.

The study inspected 36 option-matrix symbol/date windows, found 24 same-symbol non-earnings candidates, and referenced 82 existing option-event completion receipts. It performed zero provider calls. Result: zero verified no sampled option-abnormality non-earnings controls; all 24 candidate windows still had verified option abnormality, with three partial-contract-coverage cases that nevertheless emitted abnormality on successful contracts.

Judgment update: the earnings+option amplifier comparison remains blocked more strongly. The current option-event standard is too high-emission in the sampled liquid contracts to provide clean controls from either earnings dates or same-symbol non-earnings windows. Do not promote option-flow alpha or broaden EventRiskGovernor powers from this evidence. The cleaner next route is either a stricter abnormality definition with controls, or official company result/guidance interpretation for the event-alone family.

## Sixth itemized test — non-earnings option-standard saturation

Artifact: `/root/projects/trading-model/storage/option_abnormality_non_earnings_saturation_20260515/`

The reviewed option matrix already contained 34 same-symbol non-earnings symbol/date windows. Every one emitted complete option-abnormality events under the current standard, with at least 14 complete events per non-earnings symbol/date.

Judgment update: this explains why clean earnings-without-option-abnormality controls could not be found. The current option-event standard is saturated in this sample and cannot support a no-abnormality control design. Earnings/guidance remains useful only as direction-neutral event-risk context; option abnormality remains provenance/risk evidence until the abnormality standard is revised and revalidated.

## Seventh itemized test — official guidance readiness

Artifact: `/root/projects/trading-model/storage/earnings_guidance_readiness_scout_q4_2025_20260515/`

The readiness scout found official SEC result artifacts for all 12 Q4 2025 earnings events and partial result context for 11, but found zero official guidance interpretations, zero expectation baselines, and zero signed-direction-ready rows.

Judgment update: earnings/guidance remains useful as direction-neutral event-risk context only. The next acceptable evidence route is official company release/exhibit/transcript guidance interpretation plus consensus or accepted expectation baselines. Do not infer signed alpha from SEC result artifacts alone.

## Eighth itemized test — official artifact coverage gate

Artifact: `/root/projects/trading-model/storage/earnings_guidance_artifact_coverage_scout_q4_2025_20260515/`

The coverage scout consumed the Q4 2025 interpreted earnings/result rows and selected SEC result filing references. It performed zero provider calls and checked whether local official company document text artifacts exist for guidance/outlook interpretation.

Result: 12/12 events have SEC result filing references, but 0/12 have local official filing/release/transcript text artifacts, 0 accepted guidance interpretations, 0 expectation baselines, and 0 signed-direction-ready rows.

Judgment update: SEC metadata and normalized facts are not enough. Earnings/guidance remains direction-neutral EventRiskGovernor context only until official company document text is acquired, interpreted under a reviewed guidance standard, and joined to point-in-time expectation baselines.
