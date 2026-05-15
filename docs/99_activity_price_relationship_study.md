# Activity-Price Relationship Study

This study tests whether abnormal activity has a stable, point-in-time relationship to subsequent price/path outcomes across different company sizes, sectors, and event families.

It is the required proof gate before `event_activity_bridge` can be promoted into `EventActivityBridgeModel` or used as `EventRiskGovernor` risk-intervention evidence.

## Purpose

The project hypothesis is:

> Abnormal activity can standardize part of the relationship between hard-to-standardize events/news and future price or odds behavior.

The study must prove this without tautology. Price-derived activity cannot be validated against the same price interval that created it.

## Study Questions

1. Does abnormal activity predict or explain forward price/path labels after the detection window?
2. Does the relationship remain after controlling for market, sector, peer, and target-state context?
3. Does event-confirmed abnormal activity behave differently from abnormal activity with no visible event?
4. Does pre-event abnormal activity provide useful latent-event hazard evidence?
5. Do option/liquidity activity legs add value beyond ordinary price/volume activity?
6. When prediction-market data is later available, does odds activity confirm or diverge from securities activity in a useful way?

## Cohort Design

The study must be cross-sectional. A single story stock can be used for debugging, but not for acceptance.

### Size Buckets

```text
mega_large_cap
large_cap
mid_cap
small_cap
micro_or_speculative_cap
```

### Sector / Theme Buckets

Initial study buckets:

```text
technology_platform
semiconductor_ai
financials_bank_or_broker
energy_commodity
healthcare_biotech
industrial_defense_aerospace
communications_satellite
consumer_retail
crypto_sensitive
```

### Candidate Pilot Basket

This is a pilot basket, not a permanent universe. Symbols may be replaced when liquidity/news coverage is insufficient.

| Bucket | Example symbols | Rationale |
|---|---|---|
| mega/technology | AAPL, MSFT | deep liquidity, many news events, strong controls needed |
| mega/semiconductor_ai | NVDA, AMD | high event sensitivity, options-rich |
| large/financials | JPM, COIN | bank/market-structure and crypto-sensitive event channels |
| large/energy | XOM, CVX | commodity and geopolitical event sensitivity |
| large/healthcare | LLY, PFE | FDA/clinical/earnings style event contrast |
| mid/industrial-defense | RKLB, ACHR | aerospace/defense/news-contract sensitivity |
| small/communications-satellite | ASTS | financing/FCC/launch/partnership event sensitivity |
| small/defense-drone | RCAT | relatively pure drone/government-contract pilot case |
| small/consumer-retail | CAVA, ELF | consumer/earnings/social-attention contrast |
| speculative/biotech | VKTX, SAVA | clinical/regulatory event sensitivity; review for liquidity/noise |

Selection rules:

- Exclude symbols with too little daily volume or too sparse news coverage for the chosen window.
- Exclude symbols where corporate actions, listing changes, or missing data make labels unreliable unless explicitly handled.
- Keep at least one broad-market ETF and one sector/theme ETF control per bucket.
- Prefer symbols with both quiet periods and event-heavy periods.

## Event / Activity Classes

Activity classes follow the accepted abnormal-activity taxonomy:

```text
price_action_pattern
residual_market_structure_disturbance
microstructure_liquidity_disruption
option_derivatives_abnormality
```

Bridge relation classes:

```text
pre_event_precursor
co_event_reaction
post_event_absorption
event_activity_divergence
unresolved_latent_hazard
```

Event families should be evaluated separately before aggregate conclusions:

```text
earnings_or_guidance
analyst_rating_or_price_target
contract_award_or_customer_order
regulatory_or_legal
financing_or_offering
product_or_partnership
macro_policy_or_geopolitical
short_report_or_investigative_claim
clinical_or_fda
prediction_market_resolution_related
```

## Windows

The study must separate windows:

```text
activity_detection_window
event_availability_window
forward_label_window
```

Initial horizons:

```text
5m
30m
1h
1d
5d
20d
```

Daily-only runs may use `1d`, `5d`, and `20d` first. Intraday runs should be added for the cleanest event cases.

## Forward Labels

The first proof question is direction-neutral tradability: whether abnormal activity is followed by larger absolute price/path displacement. Downside paths are tradable too, so average signed return is only a secondary diagnostic.

Required direction-neutral label families:

```text
absolute_forward_return
forward_path_range
max_favorable_excursion
max_adverse_excursion
tradeable_excursion
forward_volatility_expansion
forward_gap_or_jump_abs
path_asymmetry
```

Required directional label families:

```text
activity_direction_bias
signed_forward_return
signed_directional_forward_return
forward_drawdown
forward_reversal
close_to_close_continuation
open_gap_followthrough
intraday_absorption_score
```

Rules:

- Primary activity-price proof should compare absolute forward moves and tradeable excursions between abnormal and non-abnormal windows.
- Directional alpha comes next. A strong downside relationship is useful if direction can be classified or hedged.
- Signed average forward return must not be used as the main acceptance metric because positive and negative tradable moves can cancel out.
- Direction labels are required for later model design, but they must be evaluated separately from direction-neutral tradability.

## Abnormality Coverage Completion Gate

The project must complete abnormality evidence coverage before treating any pilot as a directional conclusion. Partial slices are useful for debugging label shape, but they are not acceptance evidence.

Coverage must include all accepted abnormal-activity families before judgment:

```text
price_action_pattern
residual_market_structure_disturbance
microstructure_liquidity_disruption
option_derivatives_abnormality
```

For option-derived abnormality, coverage-complete means the study has point-in-time evidence for at least:

```text
call_put_side
aggressor_or_quote_side
ask_bid_touch_context
sweep_or_block_context
opening_or_closing_context
open_interest_or_oi_change
iv_level_and_change
skew_direction
term_structure_direction
underlying_confirmation_or_divergence
direction_confidence
```

Rules:

- If any required abnormality family is missing, outputs must be labeled `diagnostic_only_abnormality_incomplete`.
- Incomplete pilots may identify candidate hypotheses, data gaps, and label bugs, but must not produce a final bullish/bearish conclusion.
- Directional judgment must wait until the abnormality set is complete enough to distinguish demand, hedging, closing flow, dealer inventory, volatility demand, and liquidity disturbance.
- Cross-sectional testing begins after coverage is complete; simply adding more symbols with incomplete abnormality evidence does not solve the proof problem.
- `11_feed_thetadata_option_event_timeline` now emits explicit option-abnormality coverage fields for side, bid/ask touch, sweep/block, OI/opening-vs-closing, IV-change, skew, term structure, underlying confirmation/divergence, direction confidence, and missing-field status. Missing upstream evidence remains missing evidence; the feed must not fabricate coverage.

## Activity Direction Evidence

Some abnormal activity has natural directional orientation. The study must preserve this orientation rather than treating every activity token as directionless.

Accepted direction classes:

```text
bullish_activity
bearish_activity
neutral_activity
mixed_or_conflicting_activity
unknown_direction_activity
```

Directional evidence examples:

| Evidence type | Typical direction | Notes |
|---|---|---|
| call volume / call sweep / ask-side call buying surge | bullish | Requires option side/aggressor confidence; call volume alone can be hedging. |
| put volume / put sweep / ask-side put buying surge | bearish | Requires option side/aggressor confidence; put selling may be bullish, so quote side matters. |
| positive residual return or positive gap | bullish proxy | Price-derived and must be controlled for same-window tautology. |
| negative residual return or negative gap | bearish proxy | Price-derived and must be controlled for same-window tautology. |
| liquidity sweep high / false breakout / bull trap | bearish reversal proxy | Must be empirically tested; not assumed. |
| liquidity sweep low / false breakdown / bear trap | bullish reversal proxy | Must be empirically tested; not assumed. |
| IV expansion without call/put/skew side | direction unknown | Often indicates path/risk expansion rather than direction. |
| skew shift toward calls or puts | directional option evidence | Direction depends on skew definition and whether flow is buyer- or seller-initiated. |

### Option Activity Direction Study

Option activity must be handled as a directional-evidence study, not a generic volume spike. The same volume can mean different things depending on right, side, aggressor context, and whether the trade opens risk or closes/hedges risk.

Minimum option-direction evidence fields:

```text
option_right
trade_side_or_aggressor_side
ask_touch_ratio
bid_touch_ratio
sweep_or_block_context
trade_size
trade_notional
window_volume
open_interest_change
opening_or_closing_context
iv_change
skew_direction
term_structure_direction
direction_confidence
```

Initial option-direction hypotheses:

```text
ask_side_call_activity -> bullish_activity
ask_side_put_activity -> bearish_activity
bid_side_call_activity -> bearish_activity_or_call_selling
bid_side_put_activity -> bullish_activity_or_put_selling
call_put_ask_side_imbalance_positive -> bullish_activity
call_put_ask_side_imbalance_negative -> bearish_activity
iv_expansion_without_side -> unknown_direction_activity
call_skew_richening -> bullish_activity_or_upside_demand
put_skew_richening -> bearish_activity_or_downside_demand
```

Required option-direction comparisons:

1. call ask-side events vs non-event option windows;
2. put ask-side events vs non-event option windows;
3. call/put ask-side imbalance buckets;
4. IV-only expansion without side evidence;
5. sweep/block events vs ordinary prints;
6. opening-volume evidence vs ambiguous/closing-volume evidence;
7. option-direction evidence confirmed by underlying move vs option/underlying divergence.

The study should evaluate both underlying forward labels and option-forward labels when available:

```text
underlying_signed_directional_forward_return
underlying_absolute_forward_return
option_contract_signed_forward_return
option_contract_absolute_forward_return
implied_vol_forward_change
skew_forward_change
```

Important caveat: a call-buying surge is only directionally bullish when the system has enough side/aggressor/opening evidence. Otherwise it is an option-activity path-expansion signal with `unknown_direction_activity` or `review_required` direction.

Pilot evidence note: `/root/projects/trading-model/storage/option_direction_pilot_20260515_aapl/` contains a diagnostic AAPL one-date pilot using ThetaData option event timeline rows, Alpaca underlying daily bars, and ThetaData option OHLC snapshots. It validates the label shape but is not promotion evidence: one symbol/date/strike, duplicated same-day forward labels, no OI/skew/sweep/block context, and no calibrated direction confidence. The pilot also clarifies label policy: underlying directional returns are sign-adjusted by bullish/bearish hypothesis, while ask-side call/put option-contract payoff is measured as long-contract forward return and must not multiply put returns by the bearish sign.

Cross-section pilot note: `/root/projects/trading-model/storage/option_direction_cross_section_20260515/` extends the diagnostic slice to NVDA, JPM, XOM, LLY, and RKLB on the same event date. The headline result is mixed: ask-side CALL evidence is more promising than ask-side PUT evidence, especially on symbol-weighted 10d outcomes, but neither direction can be treated as a universal rule. Ask-side PUT activity was weak as a stable bearish signal in this slice. This remains `diagnostic_only_abnormality_incomplete`: it reinforces that option direction needs OI/opening-vs-closing, skew/term-structure, sweep/block, and confidence filters before judgment.

Complete-coverage cross-section note: `/root/projects/trading-model/storage/option_direction_complete_coverage_cross_section_20260515/` reruns the diagnostic direction study after enabling real ThetaData OI/IV/skew/term/underlying auto-context enrichment. It emitted 239 events across AAPL, NVDA, JPM, XOM, LLY, and RKLB; 231 passed `abnormality_coverage_complete`, and all 60 auto-context endpoint requests succeeded with no hard blockers. In the complete-evidence subset, `bullish_activity` was positive on 10d/14d directional underlying labels and long-option payoffs, while `bearish_activity` remained weak/negative outside the 5d horizon. Ambiguous classes such as `mixed_or_conflicting_activity`, `bullish_activity_or_put_selling`, and `bearish_activity_or_call_selling` remain non-directional diagnostics. This is stronger than the incomplete pilot but still not promotion evidence because it is one event date and one expiration.

Thorough matrix note: `/root/projects/trading-model/storage/option_direction_thorough_matrix_20260515/` expands the same complete-evidence diagnostic to AAPL, MSFT, NVDA, AMD, JPM, XOM, CVX, LLY, PFE, COIN, TSLA, and RKLB across event dates 2026-04-17, 2026-04-24, and 2026-05-01. It emitted 841 events; 786 passed `abnormality_coverage_complete`; 385 auto-context endpoint requests produced 4 hard blockers, all PFE 27.5 same-strike 2026-05-22 term-structure IV HTTP 472 responses. Complete-evidence `bullish_activity` stayed positive overall (10d directional avg +5.13%, hit 55.3%, long-option 10d avg +54.2%) but was symbol-unstable. Complete-evidence `bearish_activity` did not validate overall (10d directional avg -6.10%, hit 37.4%, long-option 10d avg -51.7%). This reinforces the current rule: bullish option abnormality is a candidate conditional signal, bearish option abnormality needs stricter filters or may fail, and neither should be promoted before broader date/expiry stability and matched non-event controls.

Matched-control note: `/root/projects/trading-model/storage/option_activity_matched_control_study_20260515/` compares unique complete-evidence abnormal windows from the thorough matrix against same-symbol underlying control windows matched on prior 1d absolute return, price level, and calendar distance. It produced 152 abnormal windows and 456 matched controls. This conservative pass did **not** confirm an incremental relationship: `bullish_activity` 10d path-range delta was -0.10 percentage points and 10d directional delta was -0.98 percentage points versus controls; `bearish_activity` 10d path-range delta was -0.34 percentage points with only a small +0.78 percentage-point directional delta. Controls were not separately queried as no-option-abnormality dates, so the result blocks promotion rather than permanently rejecting refined future definitions.

Strict-filter note: `/root/projects/trading-model/storage/option_activity_strict_filter_study_20260515/` tests intuitive stronger candidate definitions: net opening OI increase, positive IV change, underlying confirmation, front-month richening, and direction-supportive/neutral skew. These filters did **not** rescue the relationship. Bullish strict filters became underpowered and generally underperformed matched controls; e.g. `opening_iv_up` bullish had only 5 valid windows, 10d directional delta -5.95 percentage points, and 10d path-range delta -2.96 percentage points. Bearish strict filters sometimes improved directional deltas but remained small and had negative path-range deltas. Current option abnormality definitions therefore remain diagnostic/provenance evidence and should not be promoted without a different feature definition or stronger controlled evidence.

Event-risk amplifier note: `/root/projects/trading-model/storage/option_event_risk_amplifier_study_20260515/` tests whether option abnormality becomes useful when near Alpaca news. Raw news proximity was too broad: 147/152 abnormal windows had prior/same-day PIT news, and overall PIT-news-proximate windows did not show a robust edge versus matched controls. Family separation was more informative: `earnings_or_guidance_news` had 20 windows across 4 symbols with 10d absolute-return delta about +3.08 percentage points and 10d path-range delta about +1.47 percentage points, while `general_company_news` was negative. This supports a narrower next route: reviewed event interpretation with material event family, lifecycle, known/surprise status, and magnitude before option abnormality is used as an event-risk amplifier.

Directional proof metrics:

```text
activity_direction_bias_score
activity_direction_confidence_score
signed_directional_forward_return
directional_hit_rate
opposite_direction_failure_rate
mixed_direction_conflict_score
```

Rules:

- Direction must come from point-in-time activity evidence, not from future return labels.
- Option direction must distinguish call vs put, buy vs sell/aggressor side when available, sweep/block context, and whether the activity is opening or closing/hedging flow.
- If activity expands path but direction is weak, it can still be valuable for volatility, optionality, or risk-governor use.
- Directional proof must be stratified by activity type; e.g. call-buying evidence should not be evaluated together with IV-only expansion.

## Controls

At minimum, evaluate abnormal activity after controlling for:

- broad market return and volatility context;
- sector/theme ETF return context;
- peer basket return context;
- existing target-state features;
- ordinary bars, volume, liquidity, volatility, gap, and trend features;
- scheduled event calendar shells;
- time-of-day, day-of-week, and month effects;
- broad-market liquidity/volatility regime;
- prior momentum and prior drawdown.

## Required Comparisons

For each symbol/bucket/event family, compare:

1. all eligible windows;
2. abnormal activity windows;
3. non-abnormal windows;
4. event-only windows;
5. event + abnormal windows;
6. abnormal-without-visible-event windows;
7. pre-event abnormal windows later explained by event;
8. event/activity divergence windows.

The key acceptance question is not whether abnormal windows have a higher signed average return. It is whether specific activity classes expand absolute forward paths or tradeable excursions after controls, and whether later stages can classify direction, reversal, continuation, or risk.

## Acceptance Standard

The proof gate can pass only if evidence shows:

```text
abnormality_coverage_complete
forward_price_path_relationship
incremental_residual_value
cross_sectional_non_story_stock_support
out_of_sample_stability
leakage_controls_passed
reviewed_failure_modes
```

`abnormality_coverage_complete` must be evaluated before accepting direction or promotion evidence. Without it, the result remains a data-coverage diagnostic even if a pilot has attractive returns.

A convincing result should identify where the signal works and where it does not. It does not need every sector and every activity class to work.

Fail conditions:

- effect exists only in one story stock;
- activity only describes same-window price movement;
- signal disappears after market/sector/ordinary-feature controls;
- signal is dominated by liquidity noise in small caps;
- labels depend on hindsight event availability;
- results are unstable across time splits.

## Promotion Path

If the study passes:

1. create `EventActivityBridgeModel` as a candidate layer;
2. define bridge vector outputs and deterministic baseline scorer;
3. run family-specific and cross-family evaluations;
4. only then allow `EventRiskGovernor` to consume bridge outputs for risk intervention.

If the study fails:

- abnormal activity remains descriptive/provenance evidence;
- no model-layer promotion;
- retain useful event-review diagnostics only.

## Canonical earnings/guidance scouting control pass — 2026-05-15

Artifact: `/root/projects/trading-model/storage/earnings_guidance_event_scouting_20260515/`

This pass reran the event-risk amplifier question using canonical Nasdaq earnings-calendar shells instead of Alpaca headline-keyword `earnings_or_guidance_news` labels. It used 16 reviewed local `release_calendar.csv` artifacts for the three option-abnormality event dates plus all matched-control dates. The study itself made zero provider calls; calendar acquisition happened as a bounded source-data prerequisite in `trading-execution`.

Results:

- 10 target-symbol earnings-calendar shells were found across the event/control date range.
- 9 of 152 abnormal option windows fell on canonical earnings-shell dates, all from 2 symbols (`CVX`, `XOM`) on `2026-05-01`.
- All 152 abnormal windows had at least one verified non-earnings matched control after filtering same-symbol controls against Nasdaq calendar shells.
- Canonical earnings-shell slice: `n=9`, `n_symbols=2`, 5d absolute-return delta about +1.03 percentage points, 5d path-range delta about +0.71 percentage points, both positive in 9/9 windows.
- 10d/14d shell labels were unavailable or underpowered in the current matrix window, so the apparent 5d effect is diagnostic only.
- Non-earnings option-abnormality windows remained weak at 10d: path-range delta about -0.16 percentage points and absolute-return delta about -0.65 percentage points versus verified non-earnings controls.

Interpretation:

- Canonical event-family separation improves the evidence shape: broad raw-news proximity was saturated, while verified calendar shells create a clean event/non-event split.
- The earnings-shell slice is too small and too concentrated for promotion. It supports further event-family scouting, not activation.
- The remaining blocker is not documentation; it is coverage/evidence. Next proof requires more earnings seasons, official result/guidance artifacts, and no-option-abnormality controls verified through option-event feeds.

## Itemized test 1 — earnings/guidance scheduled-shell event-alone

Artifact: `/root/projects/trading-model/storage/earnings_guidance_event_alone_q4_2025_20260515/`

After the final event-layer judgment, the first itemized test isolated canonical earnings/guidance scheduled shells from option abnormality and raw-news proximity. The Q4 2025 12-symbol slice paired 12 earnings-shell events with 36 same-symbol non-earnings controls.

Headline deltas versus controls:

- 5d absolute forward return: +1.70 percentage points;
- 5d path range: +2.76 percentage points;
- 10d path range: +2.17 percentage points;
- 14d path range: +1.23 percentage points;
- 5d directional return: -1.69 percentage points.

This supports the event-layer boundary already chosen: event evidence is currently more defensible as direction-neutral path/risk context than directional alpha.

## Itemized test 2 — earnings/guidance official result artifacts

Artifact: `/root/projects/trading-model/storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/`

The second itemized earnings/guidance test joined scheduled shells to official SEC submission/companyfacts artifacts. It found official result artifacts for all 12 Q4 2025 events and partial reported-metric interpretation for 11 events.

The split by simple result direction remained too small and not directionally reliable: positive-result-score events had 5d path range about 11.1% and 5d directional hit rate 28.6%; negative-result-score events had 5d path range about 6.3% and 5d directional hit rate 33.3%. This continues to support event-risk/path context, not signed alpha.

## Itemized test 3 — earnings/guidance plus option abnormality split

Artifact: `/root/projects/trading-model/storage/earnings_option_abnormality_split_scout_20260515/`

A no-provider join between canonical 2026 earnings shells and the reviewed option-direction thorough matrix found only two option-covered earnings rows (`CVX`, `XOM` on `2026-05-01`). Both had verified option abnormality; none provided a verified no-option-abnormality earnings control.

The amplifier comparison is therefore blocked rather than negative or positive. Existing evidence cannot distinguish earnings-with-option-abnormality from earnings-without-option-abnormality.

## Itemized test 4 — sampled no-option-abnormality control probe

Artifact: `/root/projects/trading-model/storage/earnings_option_no_abnormality_control_probe_20260515/`

The follow-up sampled five candidate strikes and both CALL/PUT under the same option-event standard for earnings rows missing from the existing option matrix. The probe referenced 80 provider calls and the summarizing model study performed zero provider calls.

Outcome: zero verified no sampled option-abnormality controls were found. Existing-matrix rows (`CVX`, `XOM`) remained verified abnormal; six newly probed rows were verified abnormal; `PFE` and `RKLB` had partial contract coverage due ThetaData HTTP 472 but still emitted abnormality on successful sampled contracts.

This blocks the amplifier comparison. It does not prove option abnormality adds value around earnings; it only shows this sampled set did not produce the required clean counterfactual group.
