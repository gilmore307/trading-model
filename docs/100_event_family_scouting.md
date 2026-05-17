# Event Family Scouting

Status: active Layer 8 research/governance contract.

This document turns the option-abnormality proof work into a stricter route for event-risk modeling. It does **not** promote `event_activity_bridge` or raw option abnormality into a model layer.

## Purpose

Raw option abnormality and raw news proximity failed the current promotion standard. Matched controls weakened the standalone option-abnormality relationship, and simple Alpaca-news proximity was too broad to separate useful event-risk amplification from ordinary news saturation.

Future event-risk work must therefore scout coherent event families before training or promotion. The unit of study is not "all news" or "all option flow". The unit is an interpreted event family with point-in-time lifecycle clocks, materiality rules, canonical source precedence, and abnormal-activity bridge rules.

## Required `event_family_scouting_packet_v1`

Each event family must have a packet before model training or risk-intervention promotion work begins.

## Event-family granularity rule

Event-family scouting must be deliberately fine-grained. The overview categories produced by event ingestion, such as `macro_news`, `symbol_news`, `sec_filing`, or `earnings_guidance`, are routing buckets, not modeling families. They are too broad for price/path association proof and must not be trained as one mixed event model.

News must be decomposed into concrete reusable event families before association analysis. A `symbol_news` row is only a source container until interpretation assigns a narrower family such as management change, product launch, customer loss, legal action, regulatory approval/rejection, analyst-rating change, capital allocation, supply-chain disruption, or earnings/guidance narrative residual. Likewise, `macro_news` and `sector_news` must be split by policy, rates, inflation, commodity, credit/liquidity, geopolitical, regulation, demand, supply, or other reviewed mechanism.

Each narrow family must run its own `event_family_scouting_packet_v1` and price/path association study. Do not pool unrelated mechanisms merely to increase row count. Cross-family composition is allowed only after family-specific evidence, clocks, controls, and failure modes are understood.

Initial fine-grained family candidates include, but are not limited to:

| Routing bucket | Candidate event families |
|---|---|
| `earnings_guidance` | scheduled earnings shell, earnings result, guidance raise/cut, guidance withdrawal, margin/mix commentary, earnings-call narrative residual |
| `sec_filing` | equity offering/dilution, buyback/repurchase, M&A filing, insider/ownership change, legal/regulatory investigation, accounting restatement, bankruptcy/restructuring, routine filing with no material event |
| `symbol_news` | product launch/failure, management change, customer/contract win or loss, analyst rating/price-target change, lawsuit, regulatory approval/rejection, supply-chain disruption, capital allocation, strategic investment reframing |
| `sector_news` | sector regulation, commodity/input-cost shock, demand shock, technology transition, industry read-through, sector ETF/flow stress |
| `macro_data` / `macro_news` | CPI/inflation, FOMC/rates, NFP/employment, GDP/growth, retail sales/consumption, Treasury/yield-curve shock, credit/liquidity stress, fiscal/geopolitical shock |
| abnormal activity buckets | price-action pattern, residual market-structure disturbance, microstructure liquidity disruption, option derivatives abnormality |

If a candidate family is still too broad to state a plausible mechanism and matched-control design, split it again before training.

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

## Current fine-grained batch catalog

The first batch catalog is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_batch_catalog.py
```

Output artifacts live under `storage/event_family_batch_catalog_20260516/`:

- `event_family_batch_catalog.json`
- `event_family_batch_summary.json`
- `event_family_batch_queue.csv`
- `event_family_first_pass_packets.jsonl`
- `event_family_blocker_queue.csv`

The first batch contains 29 fine-grained candidate families across earnings/guidance, SEC filings, symbol news, sector news, macro events, and abnormal-activity residuals. It performs zero provider calls, model activation, broker/account mutation, or artifact deletion. The batch is a queue/readiness artifact, not proof that any family should enter training.

The first event-price association readiness slice is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_price_association_readiness.py
```

Output artifacts live under `storage/event_price_association_readiness_20260516/`:

- `event_price_association_batch.json`
- `event_price_association_family_readiness.csv`
- `event_price_association_candidate_events.csv`
- `event_price_association_price_labels.csv`

The first slice covers `equity_offering_dilution`, `legal_regulatory_investigation`, `cpi_inflation_release`, and `credit_liquidity_stress`. It produces CPI exploratory price labels from local January 2016 macro-calendar and ETF bar artifacts, but keeps CPI underpowered because there is only one local event month and no family-level controls. The other selected families remain blocked on packet/parser/source-standard work. This artifact is readiness/scouting only, not promotion evidence.

The CPI-focused local-control readiness slice is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_cpi_inflation_association_readiness.py
```

Output artifacts live under `storage/cpi_inflation_association_readiness_20260516/`:

- `cpi_inflation_association_readiness.json`
- `cpi_inflation_association_summary.json`
- `cpi_inflation_events.csv`
- `cpi_inflation_event_labels.csv`
- `cpi_inflation_control_labels.csv`
- `cpi_inflation_event_control_comparisons.csv`

The CPI slice scans available local Trading Economics calendar artifacts and Alpaca ETF bars. Current local result: 1 CPI event month (`2016-01`), 1 CPI event clock, 10 event labels, 120 same-month control labels, and 10 event/control comparisons. Status remains `underpowered_cpi_scouting_only`: the matched-control machinery exists, but the local event sample is far too small and still lacks official-source canonicalization, market/sector/target-state controls, and a preaccepted surprise definition. No association, risk-promotion, or alpha claim is made.

A follow-up diagnostic used FRED read-only CPI release dates and CPI/Core CPI observations against already-local Alpaca ETF bars:

Artifact: `storage/cpi_release_correlation_study_20260516/`

Result: 131 CPI release dates from 2016-01 through 2026-05, 1,571 strict one-day ETF/event rows across liquid ETF/sector proxies, and nearby non-event controls. Aggregate one-day event return delta versus controls was effectively zero (-0.004 percentage points), aggregate one-day absolute-return delta was effectively zero (+0.001 percentage points), and one-day path-range delta was small (+0.097 percentage points). Realized CPI/Core CPI level/change correlations with forward returns were weak and unstable: aggregate one-day correlations were about +0.05 to +0.09, while 5-10 day correlations drifted mildly negative (roughly -0.04 to -0.09 for month-over-month CPI/core and -0.08 to -0.09 for year-over-year CPI/core).

Conclusion: CPI release occurrence has weak event-risk/volatility relevance, but realized CPI level/change is not meaningful as standalone directional alpha. If included, CPI should be a macro event-risk/calendar control feature, not a trading signal or promotion-ready event family.

Abnormal CPI follow-up:

Artifact: `storage/cpi_abnormal_release_correlation_study_20260516/`

Definition: expanding historical z-score excluding the current print, `abs(z) >= 1.5`, minimum 24 prior releases, over CPI MoM, Core CPI MoM, CPI YoY, and Core CPI YoY. This identified 44 abnormal CPI release dates out of 131.

Result: abnormal releases show more event-risk/volatility relevance than normal releases, especially one-day path range. For abnormal releases, aggregate one-day path-range delta was about +0.233 percentage points versus controls, compared with about +0.027 percentage points for normal releases. Abnormal YoY/Core YoY prints were stronger on path expansion (roughly +0.405 to +0.489 percentage points one-day path delta). Directional return evidence remained weak/unstable: abnormal one-day return delta was about -0.012 percentage points overall, positive-return-delta share was about 52%, and 5-10 day abnormal return deltas were negative.

Conclusion: abnormal CPI is worth including as an abnormal macro-risk/volatility flag and control feature. It is still not a standalone directional alpha signal.

CPI surprise follow-up:

Artifact: `storage/cpi_surprise_correlation_study_20260516/`

Definition: actual-minus-forecast surprise from public Investing.com CPI event pages for CPI MoM, Core CPI MoM, CPI YoY, and Core CPI YoY, joined to local ETF bars and nearby non-event controls. Large surprise thresholds tested at 0.1 and 0.2 percentage points.

Result: the meaningful abnormal definition is the larger actual-vs-forecast miss, `abs(actual - forecast) >= 0.2pp`, which produced 33 release dates. Large CPI surprises have clearer event-risk relevance than raw CPI levels: aggregate one-day path-range delta was about +0.465 percentage points and absolute-return delta about +0.149 percentage points. Directional return remains conditional and not standalone: aggregate one-day return delta was about -0.389 percentage points, hotter surprises were more negative (about -0.534 percentage points one-day return delta, positive-delta share about 34%), and cooler surprises were less negative (about -0.216 percentage points, positive-delta share about 48%).

Conclusion: actual-vs-forecast CPI surprise is the right CPI abnormality definition. It is meaningful enough to include as an abnormal macro-risk/surprise feature, especially for event-day volatility/path risk and conditional risk-off pressure after hot surprises. It is still not robust enough to be a standalone buy/sell alpha signal.

TE canonical route check:

Artifact: `storage/te_cpi_surprise_correlation_study_20260516/`

Trading Economics visible calendar rows expose `actual`, `consensus`, and `te_forecast` fields through the existing `trading-data` feed. A TE-only probe over monthly visible-calendar windows found expectation-populated historical CPI rows for 18 release dates / 36 CPI metric rows, mostly 2016-2017 YoY rows; later visible historical rows often retain `actual`/`previous` but blank `consensus`/`te_forecast`. TE therefore remains the preferred canonical route when expectation fields are populated, but the current visible-calendar scrape is not enough by itself for the broad 2017-2026 surprise study. The larger Investing.com surprise diagnostic remains a temporary evidence source until a fuller TE expectation-history route is accepted.

The TE-only sample is too small for a final claim, but it is directionally consistent with the surprise framing: use `actual - consensus` when present, otherwise `actual - te_forecast`, and treat large CPI surprise as macro event-risk/control input rather than standalone alpha.

## Remaining batch closeout

The full remaining queue closeout is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_remaining_closeout.py
```

Output artifacts live under `storage/event_family_remaining_closeout_20260516/`:

- `event_family_remaining_closeout.json`
- `event_family_remaining_closeout_summary.json`
- `event_family_remaining_closeout.csv`
- `event_family_next_packet_queue.csv`

The closeout accounts for all 29 fine-grained families without provider calls, model activation, broker/account mutation, or artifact deletion. It promotes no family to standalone directional alpha. Current dispositions are:

- 2 risk/control candidates only: `earnings_guidance_scheduled_shell` and `cpi_inflation_release`;
- 1 deferred-low-signal family: `option_derivatives_abnormality` under the current matched-control definition;
- 20 families requiring family packets before association work;
- 3 families blocked by missing PIT expectation/comparable baselines;
- 2 residual families blocked until residual-over-base-state is defined;
- 1 liquidity-disruption family blocked until liquidity/depth evidence exists.

This closes the current batch administratively: each family has a disposition and next action, but blocked families remain blocked rather than being force-fit into an underpowered model.

## All-family precondition completion

After the remaining-batch closeout, the next safe step is to fill the precondition surface for every family before making any final association conclusion. This is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_precondition_completion.py
```

Output artifacts live under `storage/event_family_precondition_completion_20260516/`:

- `event_family_precondition_completion.json`
- `event_family_precondition_completion_summary.json`
- `event_family_scouting_packets.jsonl`
- `event_family_scouting_packets.csv`
- `event_family_evidence_requirements.csv`

The artifact emits one maintained `event_family_scouting_packet_v1` for each of the 29 families. Each packet defines source precedence, point-in-time clock rules, identity/measure fields, baseline requirements, matched controls, label windows, residual requirements, liquidity requirements, and early-stop gates.

This fills the missing-packet governance gap, but it does not claim empirical association. The final conclusion remains withheld until the required family-specific association studies exist. Remaining empirical blockers include PIT expectation/comparable baselines for earnings-result/guidance and NFP, a fuller TE expectation-history route for CPI, residual-over-base-state definitions for price/rates/market-structure residual families, liquidity/depth evidence for microstructure disruption, and a revised abnormality definition before retesting option derivatives abnormality.

## Local empirical coverage scan

The local empirical coverage/readiness scan is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_empirical_coverage.py
```

Output artifacts live under `storage/event_family_empirical_coverage_20260516/`:

- `event_family_empirical_coverage.json`
- `event_family_empirical_coverage_summary.json`
- `event_family_empirical_coverage.csv`
- `event_family_next_empirical_actions.csv`

The scan uses only existing local source/study artifacts. Current local source coverage includes 405 Alpaca news rows, 750 GDELT news rows, 24,764 SEC company-fact rows, 12 valid Trading Economics calendar rows with expectation fields, and 6,045 Alpaca bar completion receipts. It performs no provider calls, training, activation, broker/account mutation, or artifact deletion.

Coverage result: 5 families have existing empirical/scouting artifacts; 12 families have local candidate events but still need interpretation/dedup/matched-control association work; 7 families have no local candidate events under current source/parser coverage; 3 are blocked on PIT expectation/comparable baselines; 3 are blocked on residual detectors; 1 is blocked on liquidity/depth evidence; option derivatives abnormality remains deferred until its abnormality definition is revised.

## Final all-family judgment

The current-cycle final judgment is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_layer_final_judgment.py
```

Output artifacts live under `storage/event_layer_final_judgment_20260516/`:

- `event_layer_final_judgment.json`
- `event_layer_final_judgment_summary.json`
- `event_family_final_dispositions.csv`
- `event_layer_allowed_prohibited_outputs.csv`

Final answer: build the event layer as `EventRiskGovernor / EventIntelligenceOverlay`, not as a standalone event-alpha model. Current evidence accepts `cpi_inflation_release` and `earnings_guidance_scheduled_shell` for risk/control only. No family is accepted for standalone directional alpha. All other families remain blocked, deferred, or research-queue only until their family-specific evidence gates are satisfied.

## All-family association measurement

The all-family event/price association measurement is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_all_association.py
```

Output artifacts live under `storage/event_family_all_association_20260516/`:

- `event_family_all_association.json`
- `event_family_all_association_summary.json`
- `event_family_all_association.csv`
- `event_family_expanded_stability.csv`

It emits a row for every one of the 29 families. The expanded local screening pass uses every available local Alpaca bar symbol for the screening month, currently 47 ETF/proxy symbols, rather than the initial 12-symbol proxy subset. Measured positive accepted associations remain limited to risk/control: CPI surprise shows risk/volatility association, and earnings/guidance scheduled shells show direction-neutral path-risk association. The expanded stability screen identifies nine additional families as threshold-review candidates only; these are not accepted because source/parser, canonical interpretation, matched-control, PIT baseline, residual-detector, or liquidity-depth gates are still missing. Three measured families remain no-clear-local-association, four have no local measurable labels, seven remain blocked by required preconditions, three thin local candidates are unstable, and option derivatives abnormality still requires definition revision. No family supports accepted standalone directional alpha.

## Threshold/grading queue

The threshold/grading queue is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_family_threshold_grading.py
```

Output artifacts live under `storage/event_family_threshold_grading_20260516/`:

- `event_family_threshold_grading.json`
- `event_family_threshold_grading_summary.json`
- `event_family_threshold_grading.csv`

This artifact removes measured no-clear families from the active threshold/grading queue while preserving audit evidence. In this context, “delete” means delete from the next threshold queue, not physically delete source artifacts or historical evidence. Current deleted/retired queue entries are `mna_transaction`, `product_launch_or_failure`, and `sector_demand_shock` for measured no-clear local association, plus the current `option_derivatives_abnormality` definition because it has no accepted association and requires a revised abnormality standard before retesting.

Active threshold universe now contains 11 families: accepted risk/control seeds `earnings_guidance_scheduled_shell` and `cpi_inflation_release`, plus nine expanded-screening threshold-review candidates (`earnings_call_narrative_residual`, `equity_offering_dilution`, `buyback_or_capital_return`, `customer_contract_win_loss`, `management_change`, `analyst_rating_or_price_target_change`, `supply_chain_disruption`, `sector_regulation_policy`, and `commodity_or_input_cost_shock`).

No provider calls, model training/activation, broker/account mutation, destructive SQL, or artifact deletion are authorized by this queue shaping step.

## Reverse price-anomaly discovery

The reverse discovery scan is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_price_anomaly_event_discovery.py
```

Output artifacts live under `storage/price_anomaly_event_discovery_20260516/`:

- `price_anomaly_event_discovery.json`
- `price_anomaly_event_discovery_summary.json`
- `price_anomaly_events.csv`
- `price_anomaly_event_family_enrichment.csv`

This scan starts from local price anomalies first, then checks nearby event-family mentions inside a ±1-day window. The current local screen found 104 anomaly observations across 27 symbols. It identified `legal_regulatory_investigation` as the only reverse-discovery candidate under the current enrichment rule: anomaly hit rate about 48.1% versus control hit rate about 22.2%, lift about 2.17. `sector_regulation_policy` and `cpi_inflation_release` showed positive enrichment but did not pass the stronger reverse-discovery rule. Saturated event families such as analyst/customer/general macro mentions are not useful in this scan when their control hit rate is near 100%.

Reverse discovery is a hypothesis generator, not causal proof. Candidate families still require canonical event interpretation, deduplication, symbol/sector relevance, matched controls, and point-in-time clocks before threshold or model use.

## Base-stack residual anomaly route

The preferred production shape is not raw price anomaly -> event claim. The preferred route is:

```text
Layers 1-8 base stack
  -> expected market/sector/target/event-failure/alpha/position/action/option context
  -> residual_anomaly_context when observed price/path/volume/liquidity/option behavior is not explained
  -> Layer 9 event-family explanation / warning / correction overlay
```

This makes reverse discovery stricter. A price move should only become an event-model candidate when it is abnormal after the base stack explains broad market regime, sector context, target state, alpha confidence, position projection, underlying action, and option/trading guidance. The event layer then answers whether nearby events share a common family, whether the event plausibly explains the residual, and whether the right output is warning, block/cap, reduce/flatten review, uncertainty increase, or no event adjustment.

This route supports the final target: EventRiskGovernor remains a coverage, correction, explanation, and warning layer. It is not a replacement for the base trading model and does not become a standalone event-alpha model.

## Event observation pool and promotion policy

The observation-pool policy is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_observation_pool_policy.py
```

Output artifacts live under `storage/event_observation_pool_policy_20260516/`:

- `event_observation_pool_policy.json`
- `event_observation_pool_policy_summary.json`
- `event_observation_pool.csv`
- `event_promotion_rules.csv`

Research scope and realtime scope are intentionally different. During historical training/research, the system may search all point-in-time event/news/filing/macro evidence to explain residual anomalies. During realtime operation, the system should not continuously observe every possible news/event stream; it should observe only event families that have entered the reviewed observation pool or a probationary observation pool.

Current active realtime observation-pool seeds are `cpi_inflation_release` and `earnings_guidance_scheduled_shell`. Current probationary observation candidate is `legal_regulatory_investigation` because it appeared as a reverse price-anomaly discovery candidate. Other event families remain research-only until residual-anomaly evidence justifies adding them to the pool.

If a family proves stable, predictive, and incremental across controls, splits, base-stack residuals, and regimes, it may be proposed for Layer 4 EventFailureRiskModel promotion. Promotion requires a script-emitted evidence packet and final agent review. Until that reviewed promotion exists, the event family remains a Layer 9 correction/explanation/warning overlay, not a front decision input.

The residual-anomaly discovery implementation is generated by:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_residual_anomaly_event_discovery.py
```

Output artifacts live under `storage/residual_anomaly_event_discovery_20260516/`:

- `residual_anomaly_event_discovery.json`
- `residual_anomaly_event_discovery_summary.json`
- `residual_anomaly_events.csv`
- `residual_anomaly_event_family_enrichment.csv`
- `event_family_strategy_promotion_review_packets.jsonl`

This is the bridge from research to service integration: the script is manager-registerable and callable by orchestration, but it does not start services, activate models, mutate accounts, call providers, delete artifacts, or auto-promote event families.

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
