# Earnings / Guidance Event-Family Scouting Packet

Schema: `event_family_scouting_packet_v1`

Status: `scouting`

This packet defines the first dedicated event family to scout after raw option abnormality, strict option-flow filters, and raw news-proximate option abnormality failed promotion evidence. It is a governance and study packet, not a model promotion request.

## `event_family_key`

```text
earnings_guidance_event_family
```

## `family_status`

```text
scouting
```

Rationale: the raw Alpaca-news family slice labeled `earnings_or_guidance_news` was the strongest diagnostic slice in `/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/`, but it had only 20 windows across 4 symbols and used headline keywords rather than canonical earnings/report artifacts. That supports scouting only.

## `family_definition`

Scheduled or company-disclosed earnings and guidance events where an issuer reports financial results, updates forward guidance, or releases management commentary that can alter expected revenue, earnings, margins, cash flow, capex, demand, balance-sheet risk, or strategic investment interpretation.

The family includes both the pre-event scheduled catalyst shell and the post-release result/interpretation artifact, but these are separate lifecycle phases with separate visibility clocks.

## `inclusion_criteria`

Include rows when at least one point-in-time source supports one of these fact patterns:

- scheduled earnings date/window for a covered symbol;
- official earnings release, 10-Q/10-K/8-K earnings exhibit, or accepted filing containing quarterly/annual results;
- company guidance initiation, raise, cut, withdrawal, or material qualitative guidance;
- management commentary from a primary release/transcript that materially reframes results, capex, demand, margin, or strategic investment;
- credible narrative residual about market interpretation of earnings/guidance when it is linked to a canonical release artifact.

## `exclusion_criteria`

Exclude or route elsewhere:

- generic analyst ratings or price-target changes without a linked earnings/guidance fact pattern;
- ordinary market commentary that only describes price movement;
- SEC filings unrelated to operating results/guidance, such as ownership forms, routine registration statements, proxy-only governance items, or pure M&A filings;
- macro releases and sector data releases;
- post-release price reaction as an inference-time event fact;
- option abnormality alone without a visible earnings/guidance shell or release artifact.

## `canonical_source_precedence`

1. Official SEC EDGAR accepted filings and company-submitted exhibits when they contain the relevant result/guidance fact.
2. Company investor-relations earnings release, shareholder letter, webcast transcript, or official press release when captured with source timestamp and availability metadata.
3. Earnings calendar shell source for scheduling only, e.g. Nasdaq earnings calendar. Calendar phase/time may be approximate and must not provide result facts.
4. High-quality news coverage as narrative residual or secondary evidence only, especially when it explains investor interpretation of a canonical release.
5. Broad news aggregators such as Alpaca/GDELT as discovery or residual context only; they must not become the canonical result source when official artifacts exist.
6. Option/price/liquidity abnormality artifacts as bridge/activity evidence only, never as the canonical event result.

## `lifecycle_class_default`

```text
scheduled_known_outcome_later
```

The scheduled catalyst shell can be visible before release. Result, beat/miss, guidance, management commentary, and post-release interpretation are invisible until a release artifact is visible by `available_time`.

## `required_event_clocks`

```text
event_awareness_time
scheduled_time
source_published_time
source_updated_time
available_time
interpretation_time
resolution_time
reaction_window
```

Clock rules:

- `event_awareness_time`: when the market/system could know the earnings catalyst exists.
- `scheduled_time`: expected release date/window/phase when known.
- `source_published_time`: official release, filing accepted time, news publication, or transcript publication time.
- `source_updated_time`: revisions or corrected articles; updates after decision time are not inference inputs.
- `available_time`: when this system may use the source artifact.
- `interpretation_time`: when `event_interpretation_v1` or deterministic equivalent is produced.
- `resolution_time`: when the release/result phase is observable; may equal accepted filing/release time.
- `reaction_window`: evaluation-only market/option response window; never an inference input.

## `required_interpretation_fields`

Minimum result/interpreted fields when source-visible:

```text
event_phase
reported_period
release_phase
result_source_type
result_source_ref
eps_actual
eps_consensus
revenue_actual
revenue_consensus
eps_surprise_score
revenue_surprise_score
guidance_status
guidance_direction_score
guidance_magnitude_score
margin_quality_score
cash_flow_quality_score
capex_or_investment_intensity_score
balance_sheet_stress_score
management_tone_residual_score
narrative_residual_type
direction_bias_score
intensity_score
uncertainty_score
novelty_score
source_quality_score
evidence_confidence_score
review_status
standardization_status
```

Fields that are not point-in-time available must be `missing`, `partial`, or omitted according to the accepted schema; they must not be inferred from later price reaction.

## `materiality_rules`

Materiality should be scored from source facts, not market outcome:

- larger EPS/revenue surprises, guidance changes, or margin/cash-flow changes increase `intensity_score`;
- official guidance raise/cut/withdrawal is more material than ordinary commentary;
- capex or strategic-investment reframing is material when it changes the market's interpretation of future margins/growth or risk;
- balance-sheet stress, going-concern, liquidity, covenant, or financing pressure receives high materiality;
- recap/news-only items without new facts receive low novelty and may only contribute narrative residuals.

## `surprise_or_known_status_rules`

- Pre-event shell: known catalyst, unknown outcome.
- Release result: outcome becomes visible only after official release/filing/news artifact availability.
- Consensus surprise: valid only when consensus/estimate fields are point-in-time visible before release or captured by an accepted source at release time.
- Guidance surprise: valid only when prior guidance or consensus expectation is point-in-time available; otherwise record direction/magnitude with `uncertainty_score` and missing comparison notes.
- Narrative surprise: may be recorded only with evidence spans showing that market interpretation differs from headline results or prior narrative.

## `scope_routing_defaults`

- Native scope: `symbol`.
- Add `sector_or_industry` when the issuer is a sector bellwether, the release contains explicit read-through evidence, or credible coverage links the result to sector demand/supply/margin conditions.
- Add `global_market` only for mega-cap or macro-sensitive releases with broad index/rates/risk-appetite evidence.
- Use `multi_scope` when both issuer-specific and sector/global channels are supported.

## `narrative_residual_rules`

News may contribute narrative residuals when it explains why the market is repricing a canonical earnings/guidance artifact differently than raw numbers imply.

Allowed residual examples:

```text
strategic_investment_reframing
margin_mix_disappointment
guidance_quality_concern
ai_capex_or_growth_reframing
demand_pullforward_or_slowdown
liquidity_or_balance_sheet_stress
```

Narrative residuals require evidence spans and must preserve canonical relation to the official result artifact. They are event context, not alpha decisions.

## `abnormal_activity_bridge_rules`

Option, price, liquidity, and future prediction-market activity may support an `event_activity_bridge` only with explicit relation type:

```text
pre_event_precursor
co_event_reaction
post_event_absorption
event_activity_divergence
unresolved_latent_hazard
```

Rules:

- Pre-release option abnormality may be `pre_event_precursor` for latent event-risk only; it must not claim the result was known.
- Same-window option/price/liquidity abnormality around release may be `co_event_reaction`.
- Post-release abnormality may be `post_event_absorption` when it reflects digestion, disagreement, or delayed repricing.
- Divergence between strong result and weak reaction, weak result and strong rally, or option flow and underlying behavior may be `event_activity_divergence`.
- Bridge evidence must preserve separate activity detection, event availability, and forward-label windows.

## `control_design`

Required controls before pilot training:

- same-symbol non-earnings windows verified against earnings calendar/report artifacts;
- same-symbol earnings windows without option abnormality, when available;
- matched prior return, realized volatility, liquidity, market/sector return, and price-level controls;
- sector/bellwether controls for sector read-through claims;
- matched release phase/time-of-day controls where scheduled phase is relevant;
- no-option-abnormality controls verified through the option-event feed for the compared contracts or a reviewed proxy universe.

## `forward_label_design`

Evaluate direction-neutral path first, then directional evidence separately.

Required label families:

```text
absolute_forward_return
forward_path_range
max_favorable_excursion
max_adverse_excursion
tradeable_excursion
forward_volatility_expansion
signed_directional_forward_return
directional_hit_rate
post_event_reversal
option_contract_forward_return
iv_forward_change
skew_forward_change
```

Initial horizons:

```text
1d
5d
10d
14d
20d
```

Intraday horizons may be added only when source/release times and market session alignment are point-in-time reliable.

## `minimum_coverage_gate`

Do not advance beyond `scouting` unless a bounded packet has at least:

- canonical event shell/result linkage for each event window;
- at least 50 interpreted earnings/guidance windows for pilot review, unless Chentong explicitly accepts a smaller diagnostic slice;
- at least 20 symbols and at least 4 sectors/themes;
- multiple earnings seasons or a documented reason why a narrower date slice is only diagnostic;
- verified non-event controls;
- explicit missing/partial fields for unavailable consensus/guidance/option context;
- reviewed leakage check showing no result fields before release visibility.

## `early_stop_criteria`

Downgrade to `deferred_low_signal` or `retired_no_signal` if:

- canonical source linkage cannot be established for most windows;
- consensus/guidance fields are missing too often to support surprise/magnitude labels;
- matched controls erase the path/directional effect;
- effect is concentrated in one mega-cap or one earnings season;
- option abnormality adds no incremental value beyond known earnings-event risk;
- lifecycle clocks are too ambiguous to avoid leakage.

## `review_required_triggers`

Require review for:

- conflicting official and news interpretations;
- guidance withdrawal/cut, going-concern, liquidity stress, fraud, restatement, or auditor-change language;
- high-impact mega-cap releases with broad market read-through;
- major sector bellwether read-through claims;
- low-confidence consensus/surprise values;
- any event-risk intervention stronger than `explain_only`.

## `accepted_examples`

- Scheduled earnings date known before release; no result fields until official release/filing is available.
- Official 8-K earnings exhibit reports results and guidance; interpretation records result/guidance fields after `available_time`.
- News says investors reward heavy AI capex despite margin pressure; official release is canonical, news is narrative residual.
- Pre-release option IV/volume abnormality before a visible earnings date; bridge relation is `pre_event_precursor`, not leaked result knowledge.

## `near_miss_examples`

- Analyst raises price target after earnings without new company facts: route to analyst-rating family or narrative residual linked to the canonical earnings event.
- News article recaps share price movement after results with no new interpretation: low novelty, covered by canonical event.
- SEC 13F/ownership filing near earnings: not an earnings/guidance event unless it directly references results/guidance.

## `negative_examples`

- Using post-release stock return to infer whether earnings were good before the release was visible.
- Treating every high-volume pre-earnings option print as bullish or bearish.
- Merging pre-event scheduled shell, release result, and post-event reaction into one row with one timestamp.
- Treating Alpaca/GDELT headline keywords as canonical earnings results.

## `source_artifact_refs`

Current accepted or candidate refs:

```text
NASDAQ_EARNINGS_CALENDAR                 # scheduling shell only; release phase approximate
08_feed_sec_company_financials           # official SEC EDGAR filings/facts route
03_feed_alpaca_news                      # news/narrative residual or discovery only
05_feed_gdelt_news                       # broad news context/discovery only
11_feed_thetadata_option_event_timeline  # option abnormality bridge evidence only
01_feed_alpaca_bars                      # underlying labels/controls only
```

Company IR press releases/transcripts are desired canonical/narrative sources but require a separate accepted feed route before automated study use.

## `study_artifact_refs`

Diagnostic predecessors:

```text
/root/projects/trading-model/storage/option_activity_matched_control_study_20260515/
/root/projects/trading-model/storage/option_activity_strict_filter_study_20260515/
/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/
```

`trading-data` now supports materializing canonical overview rows for the first shell/result boundary: `calendar_discovery` `release_calendar.csv` rows from `nasdaq_earnings_calendar` become `earnings_guidance` scheduled-shell rows, and SEC 10-Q/10-K or earnings-related 8-K rows become `earnings_guidance` result-artifact rows. These are event-overview rows only; full interpretation and verified controls still remain future scouting work.

## Current conclusion

`earnings_guidance_event_family` is the first event family worth scouting because its raw-news diagnostic slice had a positive direction-neutral path signal. It is not yet promotion evidence. The next implementation task should build verified non-event/non-earnings controls and then rerun the option-abnormality amplifier test using the canonical shell/result rows instead of headline keywords.

## Canonical scouting control pass — 2026-05-15

Artifact: `/root/projects/trading-model/storage/earnings_guidance_event_scouting_20260515/`

A bounded canonical-calendar pass was run after the shell/result overview route was implemented. It used reviewed Nasdaq earnings-calendar `release_calendar.csv` artifacts for all tested option-abnormality dates and matched-control dates.

Findings:

- target-symbol calendar shells found: 10;
- abnormal windows tested: 152;
- abnormal windows on canonical earnings-shell dates: 9;
- symbols in shell slice: 2 (`CVX`, `XOM`);
- verified non-earnings controls available: 152/152 windows;
- shell-slice 5d absolute-return delta: about +1.03 percentage points;
- shell-slice 5d path-range delta: about +0.71 percentage points;
- shell-slice 10d/14d evidence: unavailable or underpowered in the current matrix.

Decision: this completes the first canonical shell/control scouting slice, but does not satisfy the minimum coverage gate. The family remains `scouting`. It should not advance to `pilot_training` until official result/guidance artifacts and verified no-option-abnormality controls are added across more earnings seasons.

## Event-alone scheduled-shell scout — Q4 2025 slice

Artifact: `/root/projects/trading-model/storage/earnings_guidance_event_alone_q4_2025_20260515/`

A first event-alone test was run for the Q4 2025 earnings season slice using canonical Nasdaq earnings-calendar shells and daily Alpaca equity bars for 12 target symbols. The study code performs no provider calls; bounded prerequisite acquisition produced 32 successful Nasdaq calendar artifacts and 12 equity-bar artifacts.

Scope:

- symbols: `AAPL`, `MSFT`, `NVDA`, `AMD`, `JPM`, `XOM`, `CVX`, `LLY`, `PFE`, `COIN`, `TSLA`, `RKLB`;
- event windows: 12;
- same-symbol non-earnings controls: 36, three per event;
- controls exclude dates within ±3 calendar days of a Nasdaq earnings shell for the same symbol;
- official result/guidance interpretation is not included;
- option-abnormality absence is not verified for controls.

Findings versus controls:

- 5d absolute-return delta: about +1.70 percentage points;
- 5d path-range delta: about +2.76 percentage points, positive in 75% of events;
- 10d path-range delta: about +2.17 percentage points, positive in 66.7% of events;
- 14d path-range delta: about +1.23 percentage points, positive in 66.7% of events;
- directional 5d delta was negative, about -1.69 percentage points.

Interpretation: earnings calendar shells show a cleaner direction-neutral path-expansion relationship than the broad option-abnormality definition, but this is still scouting only. It supports continued family-specific testing, not alpha promotion. The next required test is official result/guidance interpretation, then earnings-with-option-abnormality versus earnings-without-option-abnormality.

## Official result-artifact scout — Q4 2025 slice

Artifact: `/root/projects/trading-model/storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/`

A follow-up official-result slice joined the 12 Q4 2025 canonical earnings shells to local SEC submission/companyfacts artifacts. The study itself performs no provider calls; bounded prerequisite SEC acquisition produced 23 successful SEC artifacts and one failed/truncated JPM `sec_company_fact` artifact, which is recorded as missing/partial rather than fabricated.

Scope:

- event windows: 12;
- official SEC result artifacts found: 12;
- partial official result interpretations from SEC XBRL metric direction: 11;
- guidance interpretations: 0;
- reported-metric interpretation uses only simple YoY direction for revenue, net income, and diluted/basic EPS when available;
- consensus beat/miss, guidance raise/cut, and management-commentary interpretation remain missing.

Findings:

- positive reported-result score bucket: 7 events, 5d path range about 11.1%, 10d path range about 14.6%, 5d directional hit rate 28.6%;
- negative reported-result score bucket: 3 events, 5d path range about 6.3%, 10d path range about 8.5%, 5d directional hit rate 33.3%;
- missing/flat score bucket: 2 events, very high path range but directionally negative in this tiny slice;
- the result-score split is underpowered and not a signed-alpha result.

Interpretation: SEC result artifacts improve canonical coverage and confirm that official result visibility can be joined point-in-time, but the current simple metric-direction split still supports risk/path context more than direction. The next required route is true guidance/result interpretation from official company release/exhibit/transcript artifacts plus verified no-option-abnormality controls.

## Earnings + option-abnormality split scout — existing reviewed option matrix

Artifact: `/root/projects/trading-model/storage/earnings_option_abnormality_split_scout_20260515/`

A bounded no-provider diagnostic joined the canonical 2026 earnings shells to the reviewed complete-evidence option-abnormality matrix. This was the first check toward `earnings/guidance + option abnormality` versus `earnings/guidance without option abnormality`.

Scope:

- canonical earnings shells: 10;
- option-matrix requested dates: `2026-04-17`, `2026-04-24`, `2026-05-01`;
- option-covered earnings rows: 2 (`CVX`, `XOM` on `2026-05-01`);
- earnings rows with verified option abnormality: 2;
- earnings rows with verified no-option-abnormality controls: 0;
- not option-covered earnings rows: 8.

Findings for the two covered rows:

- 1d path range about 3.13%;
- 5d path range about 7.44%;
- both 5d directional returns were negative;
- direction-hypothesis rows were mixed, including bullish, bearish, put-selling/call-selling, and mixed/conflicting classes.

Interpretation: the requested amplifier comparison remains blocked because the reviewed local option artifact has no earnings-without-option-abnormality control group. Do not claim an earnings+option amplifier edge until matched earnings dates with verified no-option-abnormality coverage are acquired or verified.

## Sampled no-option-abnormality control probe

Artifact: `/root/projects/trading-model/storage/earnings_option_no_abnormality_control_probe_20260515/`

After the first split scout found no verified earnings-without-option-abnormality controls, a bounded contract-level probe sampled the remaining canonical earnings shells under the same option-event standard used by the option matrix.

Scope:

- canonical earnings shells: 10;
- existing matrix-covered abnormal earnings rows: 2;
- newly sampled earnings rows: 8;
- sampled contracts for new rows: five candidate strikes × CALL/PUT = 80 provider-referenced probes;
- sampled-contract verification only: this is not full-chain no-abnormality proof.

Result:

- verified no sampled option-abnormality controls: 0;
- verified option abnormality from existing matrix: 2 earnings rows;
- verified option abnormality from new sampled probes: 6 earnings rows;
- partial contract coverage with verified option abnormality: 2 earnings rows (`PFE`, `RKLB`), because some sampled contracts returned ThetaData HTTP 472 while successful sampled contracts still emitted abnormality.

Interpretation: the earnings+option amplifier comparison remains structurally blocked. The current sample did not produce a clean earnings-without-option-abnormality control group, so do not infer positive or negative amplifier value.

## Same-symbol non-earnings option-control verification

Artifact: `/root/projects/trading-model/storage/same_symbol_non_earnings_option_control_verification_20260515/`

After the earnings-date sampled probe found zero clean controls, the next bounded route changed the control design rather than overfitting the same earnings sample. It reused existing local option-event matrix receipts and classified same-symbol option windows by distance to the canonical Nasdaq earnings shell. Controls exclude dates within ±3 calendar days of a same-symbol earnings shell.

Scope:

- canonical earnings shells: 10;
- option-matrix symbol/date windows inspected: 36;
- same-symbol non-earnings candidate windows: 24;
- existing option-event completion receipts referenced: 82;
- provider calls performed by this study: 0;
- no-option verification scope: sampled contract/date receipts only, not full-chain proof.

Result:

- verified no sampled option-abnormality non-earnings controls: 0;
- verified same-symbol non-earnings option-abnormality windows: 24/24 candidate windows;
- 21 candidate windows had full sampled-contract success with option abnormality;
- 3 candidate windows had partial contract coverage but still emitted option abnormality on successful contracts.

Direction-neutral labels are present for the candidate windows, but they are not promotion evidence because the clean no-option-abnormality control group is still absent. The result strengthens the block: under the current option-event standard, liquid sampled contracts emit abnormalities too frequently to supply clean controls from this local same-symbol matrix. The next route should either tighten the abnormality definition before another control search, or move back to event-alone official result/guidance interpretation where controls are already cleaner.

## Option-standard saturation diagnosis

Artifact: `/root/projects/trading-model/storage/option_abnormality_non_earnings_saturation_20260515/`

A no-provider local study reused the reviewed complete-evidence option matrix and canonical earnings shells to test whether same-symbol non-earnings windows can produce clean no-option-abnormality controls under the current option-event standard.

Scope:

- reviewed option matrix symbol/date windows: 36;
- canonical earnings-shell overlaps: 2;
- same-symbol non-earnings windows: 34;
- non-earnings verified no-abnormality windows: 0;
- minimum complete option events per non-earnings symbol/date: 14.

Conclusion: the current option-event standard is saturated for this control design. It emits complete option-abnormality events not only around earnings shells but across all reviewed non-earnings symbol/date windows in the sample. The next route is not more searching inside this sample; it is either a stricter abnormality standard or a different broader control universe before retesting earnings+option amplifier value.
