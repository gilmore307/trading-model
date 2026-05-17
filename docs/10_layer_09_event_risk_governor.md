# Layer 09 — EventRiskGovernor / EventIntelligenceOverlay

<!-- ACTIVE_LAYER_REVISION -->
Status: active architecture revision. Conceptual Layer 9; implementation package and scripts now use `model_08_event_risk_governor`. The upstream data source still uses `source_08_event_risk_governor` until a separate data/SQL surface migration is accepted.

Active boundary: Layer 9 is the event-intelligence and event-risk governor after base trading guidance. It consumes standardized point-in-time event interpretations when available (`event_interpretation_v1`) plus event evidence refs, current context states, and the Layer 8 base trading guidance candidate.

It may directly modify the decision/risk record consumed by execution risk-control: block new entries, cap exposure, reduce exposure, nominate flatten/clear candidates, halt trading candidates, or require human review. It must keep the base Layer 8 guidance and event-adjusted guidance side by side for audit.

Forbidden boundary: Layer 9 must not directly send broker orders, choose routes/time-in-force, or mutate accounts. Flattening/clearing requires high-confidence high-severity evidence plus accepted execution risk policy or human review path.
<!-- /ACTIVE_LAYER_REVISION -->


Status: accepted Layer 9 design route; deterministic V1 scaffold implemented in `src/models/model_08_event_risk_governor/`.

## Purpose

`EventRiskGovernor / EventIntelligenceOverlay` is Layer 9. It converts point-in-time visible event evidence into an `event_risk_intervention / event_context_vector` for the current market, sector, target, and Layer 8 guidance context.

Layer 9 answers:

- Which events are visible at this decision time?
- Are those events macro, sector, industry, theme, peer-group, symbol, or microstructure scoped?
- How relevant is each event to the current anonymous target candidate?
- Does the event support or conflict with the current `target_context_state`?
- Does the event raise uncertainty, gap risk, reversal risk, liquidity-disruption risk, or contagion risk?
- How reliable, fresh, complete, and conflict-free is the event evidence?

Layer 9 does **not** answer alpha, trade, expression, sizing, or execution questions. It must not emit buy/sell/hold, final action, position size, option contract, strike, DTE, delta, order instruction, or account-specific decision fields.

## Residual-anomaly discovery and correction workflow

The accepted event-model workflow is two-sided:

1. **Base-stack first:** Layers 1-8 analyze the market, sector, target, accepted event-failure risk, alpha confidence, position projection, underlying action, and option/trading guidance context. Their job is to explain the normal trading state without event shortcuts.
2. **Residual anomaly detection:** price/path/volume/liquidity/option behavior that remains abnormal after conditioning on Layers 1-8 becomes a `residual_anomaly_context`, not an event conclusion.
3. **Event explanation:** Layer 9 inspects point-in-time event evidence around the residual anomaly and asks whether a canonical event family plausibly explains, amplifies, or contradicts the anomaly.
4. **Overlay output:** if evidence is strong enough, Layer 9 emits warning, explanation, uncertainty, path-risk, block/cap/reduce/flatten-review, or human-review hints. It keeps base Layer 8 guidance and event-adjusted guidance side by side.
5. **Correction boundary:** corrections are risk/explanation overlays only. They may modify confidence, risk caps, entry permission, or review requirements, but they must not replace Layers 1-8 with standalone event alpha or direct execution decisions.

This workflow prevents event evidence from becoming a broad news-alpha model. Events are used to explain and correct residual anomalies, and to warn when a known event family is visible before the base stack fully reprices it.

## Event observation pool and strategy-promotion route

Historical research and realtime operation have different event scopes:

- **Historical/model research:** may scan all point-in-time events, news, filings, macro releases, and other visible evidence to explain residual anomalies. This is how new event families enter consideration.
- **Realtime operation:** must not continuously read/classify every possible news item. It should observe only reviewed event families in the `event_observation_pool`, plus probationary families explicitly accepted for monitoring.

A family enters the realtime observation pool only after residual-anomaly research shows that it repeatedly explains abnormal behavior or carries accepted risk/control value. For example, if residual anomaly analysis repeatedly finds that war/geopolitical outbreak news explains market dislocations, a war/geopolitical family may enter the observation pool so realtime trading watches that family continuously.

A family may be proposed for promotion above the correction layer only when evidence shows stable, predictive, repeatable market reaction across splits, controls, base-stack residuals, and regimes. In that case the event family may become a strategy-decision candidate rather than a correction-only overlay. This promotion is not automatic: the script must emit an evidence packet and call an agent review for final accept/defer/reject before manager records any production scope change.

Current policy artifact:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_event_observation_pool_policy.py
```

Output: `storage/event_observation_pool_policy_20260516/`.

## Residual-anomaly discovery implementation

The first code path for the accepted architecture is:

```bash
PYTHONPATH=src python3 scripts/models/model_08_event_risk_governor/build_residual_anomaly_event_discovery.py
```

Output: `storage/residual_anomaly_event_discovery_20260516/`.

This builder starts from current physical Layer 8/governor evaluation labels over the Layers 1-8 base-stack decision path, identifies residual anomalies such as missed no-trade moves or negative-utility actions, then searches nearby PIT event families for explanations. It emits event-family enrichment rows and, when evidence is strong enough, `event_family_strategy_promotion_review_packet_v1` rows for agent review.

The current local Layer 7 label substrate is saturated: all available `2016-01` underlying-action labels are `no_trade` with missed positive utility, so non-residual controls are unavailable in this slice. The artifact therefore connects the code/service surface but deliberately emits no observation-pool addition and no strategy-promotion packet until non-residual controls exist.

## Position and input chain

Layer 9 is an event-context overlay on top of the accepted state stack:

```text
market_context_state
+ sector_context_state
+ target_context_state
+ source_08_event_risk_governor
+ event_detail_artifacts
+ scope_mapping_metadata
+ sensitivity_metadata
  -> EventRiskGovernor / EventRiskGovernor
  -> event_risk_intervention / event_context_vector
```

The upstream states are reviewed context inputs, not raw feature shortcuts. Layer 9 may use ticker/symbol identity for event matching, routing, and audit, but model-facing fitting vectors must keep raw ticker/company identity outside the payload.

## Inputs

Production inference inputs must be point-in-time only:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_context_state_ref
source_08_event_risk_governor rows visible by available_time
canonical-event and dedup metadata visible by available_time
event_detail_artifact references visible by available_time
scope_mapping_metadata visible by available_time
sensitivity_metadata visible by available_time
```

### Input A - `source_08_event_risk_governor`

`trading-data` owns the current one-row-per-event overview table:

```text
source_08_event_risk_governor
```

Current SQL overview fields:

```text
event_id
canonical_event_id
dedup_status
source_priority
coverage_reason
covered_by_event_id
event_time
available_time
information_role_type
event_category_type
scope_type
symbol
sector_type
title
summary
source_name
reference_type
reference
```

The table is intentionally light. It indexes visible event/evidence rows, records canonical-event deduplication status, and points to details; it does not store full news text, SEC filings, browser/agent analysis transcripts, detector payloads, model scores, labels, or trade recommendations.

Deduplication is part of the event-quality contract. Official SEC/exchange/company/regulatory disclosures should become canonical events when they cover the same underlying fact pattern as derivative news coverage. News rows that merely summarize the official event should use `dedup_status=covered_by_canonical_event`, `canonical_event_id`/`covered_by_event_id` pointing to the official row, and should not contribute another independent event-presence count or alpha factor. Such rows may still support attention, propagation, confirmation/conflict, or quality context. News rows may become `new_information` only when browser/agent analysis of the provided article/filing links finds genuinely new point-in-time information not already represented by the canonical event.

Future extensions such as `event_native_scope_type`, `declared_scope_type`, `industry_type`, `theme_tags`, revision ids, source update timestamps, and structured analysis-report links require separate migration and registry review before they become active schema.

### Input B - event detail artifacts

The overview row can reference type-specific artifacts. These artifacts may include:

- news artifact: headline, summary, full-text reference, source timestamps, source quality, topic/entity tags, novelty, confirmation/conflict, and revision metadata;
- SEC filing artifact: form type, accepted time, filing URL/path, materiality, dilution, ownership-change, legal, guidance, or M&A risk scores;
- macro calendar artifact: scheduled/release time, actual/consensus/previous values, surprise score, importance, revision, and asset-sensitivity maps;
- equity abnormal activity artifact: residual/trigger evidence derived from point-in-time market data, with source refs and detector metadata, only when the anomaly is not already being consumed as an ordinary upstream bar/liquidity state feature;
- price-action artifact: prior range high/low, breakout or breakdown excursion, close-back-inside evidence, upper/lower wick rejection, sweep/trap token, and detector threshold metadata;
- option abnormal activity artifact: IV shock, skew change, term-structure shift, unusual volume, call/put imbalance, large trade, sweep/block indicators, OI change, option liquidity, spread widening, and dealer-flow context when reviewed.

Artifacts must remain point-in-time versioned. A later article revision, later SEC interpretation, or post-event price reaction can be a training/evaluation label only; it cannot be an inference feature.

### Abnormal-activity residual boundary

Layer 9 abnormal-activity evidence must not double-count model-owned bars, volume, spread, liquidity, volatility, gap, VWAP, trend, or target-state features that already enter Layer 1-8 inputs.

Accepted abnormal-activity evidence categories:

```text
price_action_pattern
residual_market_structure_disturbance
microstructure_liquidity_disruption
option_derivatives_abnormality
```

Accepted uses:

- `price_action_pattern`: false breakout, failed breakdown, liquidity sweep high/low, bull trap, bear trap, or similar event-shaped behavior represented as a compact token with refs rather than duplicated raw feature columns;
- `residual_market_structure_disturbance`: an anomaly remains material after conditioning on upstream market/sector/peer/target state and is represented as unexplained board/tape disturbance;
- `microstructure_liquidity_disruption`: spread widening, depth disappearance, one-sided prints, halt/pause/anomalous quoting, or liquidity-quality degradation outside broad-market liquidity context;
- `option_derivatives_abnormality`: reviewed IV/skew/term-structure shock, unusual option volume, call/put imbalance, sweep/block evidence, OI change, or option liquidity disruption not already consumed by the base option-expression path;
- trigger/provenance evidence: a detector may explain why an event evidence row exists and point back to the bars/liquidity/option refs used to detect it.

Forbidden uses:

- re-emitting ordinary `equity_bar`, `equity_liquidity_bar`, or derived target-state values as a second independent event factor;
- treating every high return/volume/spread z-score as a standalone event when the same information is already available in upstream state vectors;
- using abnormal-activity detector thresholds as production labels or promotion gates without reviewed historical calibration;
- allowing post-event realization to become an inference-time abnormality feature.

Training implication: EventRiskGovernor must prove incremental value over upstream context states. Abnormal-activity-only baselines are diagnostic baselines, not proof that duplicated bars have new event value.

### Event-activity bridge contract

Some raw news and narratives are difficult to standardize immediately. Layer 9 may convert them into an auditable `event_activity_bridge` when observable activity gives a cleaner point-in-time structure than semantic news classification alone.

The bridge connects event evidence to price, flow, liquidity, option, and prediction-market behavior. It does not claim hidden knowledge; it records lead/lag, residual activity, and cross-market confirmation or divergence.

Accepted relation types:

```text
pre_event_precursor
co_event_reaction
post_event_absorption
event_activity_divergence
unresolved_latent_hazard
```

Core bridge fields:

```text
linked_event_ref
activity_evidence_refs
activity_window
event_window
lead_lag_seconds
residual_activity_score
cross_market_confirmation_score
option_confirmation_score
prediction_market_confirmation_score
explanation_status
```

Accepted `explanation_status` values:

```text
explained_by_known_event
partially_explained
unexplained
later_explained
review_required
```

Rules:

- `pre_event_precursor`: abnormal activity appears before the linked event is publicly visible. This is latent-event hazard evidence, not proof that the future event was known.
- `co_event_reaction`: abnormal activity appears at or near event visibility and measures immediate interpretation/attention.
- `post_event_absorption`: abnormal activity after visibility reflects absorption, disagreement, delayed repricing, liquidity stress, or second-order interpretation.
- `event_activity_divergence`: event and activity disagree, e.g. big news/no reaction, small news/large reaction, asset move/no news, or prediction-market odds move/no securities move.
- `unresolved_latent_hazard`: activity remains unexplained point-in-time; if a later canonical event explains it, add a new `later_explained` bridge record rather than rewriting history.

Prediction-market odds can be an activity leg. For Polymarket-style use, the bridge should preserve odds movement as `prediction_market_confirmation_score` or divergence evidence, not as a securities-only signal.

Golden bridge cases:

| Case | Relation type | Standardized bridge meaning |
|---|---|---|
| Option IV/volume rises before earnings/news | `pre_event_precursor` | Latent-event hazard increased before public result; do not claim the result was known. |
| News appears and stock/option/odds move immediately | `co_event_reaction` | Event was visible and market behavior confirms attention/repricing. |
| News appears but price/odds do not react | `event_activity_divergence` | Either priced-in, low relevance, low credibility, or market disagreement; requires interpretation/review. |
| Asset/options/odds move first, canonical news appears later | `unresolved_latent_hazard` -> `later_explained` | Earlier activity may become retrospectively linked for training labels, but inference-time record remains point-in-time. |

### Activity-price relationship proof gate

Before `event_activity_bridge` can be promoted into a separate model layer or used as risk-intervention evidence, the project must first prove that abnormal activity has a stable relationship to subsequent price/path outcomes.

This proof is not satisfied by showing that price-derived activity is correlated with the same price window. It must be point-in-time and forward-looking.

Required proof levels:

```text
contemporaneous_association
forward_price_path_relationship
incremental_residual_value
cross_market_confirmation_value
out_of_sample_stability
```

Minimum label families:

```text
forward_return
forward_drawdown
forward_reversal
forward_volatility_expansion
forward_gap_or_jump
path_asymmetry
```

Required horizons should include short and event-relevant windows, for example:

```text
5m
30m
1h
1d
5d
20d
```

Controls/baselines:

- market, sector, and peer return context;
- already-modeled target-state features;
- ordinary bars/volume/liquidity/volatility features;
- scheduled-event calendar shells;
- time-of-day/day-of-week/month effects;
- broad-market liquidity and volatility regime.

Evidence rules:

- Price-action abnormality must prove incremental forward relationship beyond the price features used to detect it.
- Option/derivatives abnormality should be tested both alone and after controlling for underlying price/volume/liquidity state.
- Microstructure abnormality must distinguish liquidity-quality deterioration from ordinary high-volume trading.
- Residual market-structure disturbance must condition on market, sector, peer, and target-state context before claiming residual value.
- Prediction-market activity, once added, must be tested both as confirmation and as divergence evidence against securities activity.

Promotion rule: if abnormal activity only explains the current move but does not improve forward price/path labels out of sample, it remains descriptive evidence and must not become an `EventActivityBridgeModel` layer input for risk intervention.

### Input C - upstream context states

Layer 9 consumes slim, reviewed state/context outputs:

```text
market_context_state_ref
sector_context_state_ref
target_context_state_ref
```

The relevant state information includes broad market risk/stability/liquidity context, sector trend/stability/liquidity/handoff context, and target direction/trend/path/noise/transition/liquidity/tradability context. Layer 9 uses these to decide whether an event is amplified, dampened, aligned, conflicting, or irrelevant for the current target.

### Input D - scope mapping and sensitivity metadata

Layer 9 needs mapping metadata for event-to-target relevance:

```text
target_internal_id_for_join
symbol_for_join_only
sector_type
industry_type
peer_group_id
theme_tags
index_membership
ETF_basket_membership
supply_chain_tags
country_exposure
currency_exposure
commodity_exposure
market_beta_bucket
sector_beta_bucket
rate_sensitivity_score
oil_sensitivity_score
dollar_sensitivity_score
volatility_sensitivity_score
earnings_sensitivity_score
option_liquidity_bucket
shortability_bucket
```

These fields are for join, routing, sensitivity, and audit. The model-facing vector should receive derived relevance/impact scores, not raw ticker identity.

## Point-in-time rules

Layer 9 is a high-leakage-risk layer. The primary visibility rule is:

```text
event_visible := event.available_time <= decision_available_time
```

Do not replace this with `event_time <= decision_time`. Scheduled future events can be visible before they happen; revised articles can become visible after the original article; detector rows can be generated after the bar window closes.

Recommended event clocks:

```text
event_awareness_time
event_scheduled_time
event_effective_time
event_actual_time
source_published_time
source_updated_time
ingested_time
available_time
interpretation_time
resolution_time
decision_time
tradeable_time
```

Clock meanings:

- `event_awareness_time` is when the market/system could know that a catalyst or event risk exists.
- `event_scheduled_time` is the planned report/release/meeting/court/FDA/calendar time or expected window, when known before the outcome.
- `event_effective_time` is when the event becomes economically or legally effective, if distinct from publication.
- `event_actual_time` is the fact/result occurrence time reported by the source.
- `source_published_time` / `source_updated_time` are source clocks; revisions after the decision time are not inference inputs.
- `ingested_time` / `available_time` are system point-in-time clocks; model visibility uses `available_time`.
- `interpretation_time` is when `event_interpretation_v1` is produced.
- `resolution_time` is when a delayed or multi-stage outcome becomes known.
- `decision_time` / `tradeable_time` are downstream decision and market-action clocks.

Accepted lifecycle types:

```text
scheduled_known_outcome_later
unscheduled_surprise
scheduled_recurring_data_release
multi_stage_developing_event
unknown
```

Lifecycle type is different from lifecycle state. The type says whether the event/catalyst was knowable before its result; the state says where the current row sits in the event arc.

Recommended lifecycle states:

```text
scheduled_future
pre_event_window
live_release_window
post_event_initial_reaction
post_event_decay
developing_update
resolved
stale_event
unknown
```

Training/evaluation datasets may include realized future outcomes as labels. Inference rows and `event_risk_intervention / event_context_vector` must not include post-event outcomes, hindsight event interpretations, future source revisions, or future price/option paths.

## Event-family scouting gate

Raw news proximity and raw abnormal option flow are not enough to promote an event-risk input. Before Layer 9 uses an event family for model training or risk-intervention evidence, the family needs an `event_family_scouting_packet_v1` as defined in `docs/100_event_family_scouting.md`.

The scouting packet must define the family, inclusion/exclusion rules, source precedence, lifecycle clocks, materiality/surprise rules, scope routing, abnormal-activity bridge rules, control design, forward labels, coverage gates, and early-stop criteria.

Current accepted status from the option/news diagnostics:

- standalone option abnormality: `deferred_low_signal`;
- threshold-only strict option abnormality refinement: `deferred_low_signal`;
- raw option abnormality + raw news proximity: `deferred_low_signal`;
- earnings/guidance event family: `scouting` only, not promotion evidence; packet details live in `docs/101_earnings_guidance_event_family_packet.md`.

## Event lifecycle contract

Layer 9 must not treat scheduled catalysts and surprise events as the same training object.

### Scheduled-known / outcome-later events

Examples: earnings dates, macro calendar releases, FOMC meetings, FDA decision dates, court dates, shareholder votes, and known reporting deadlines.

Contract:

- A pre-event row may say the catalyst exists and may affect gap/volatility/risk appetite.
- Result fields such as actual values, beat/miss, guidance, decision outcome, vote result, or official action are forbidden until an artifact containing the result is visible by `available_time`.
- Pre-event risk evaluation, release-result interpretation, and post-event reaction labels are separate phases.
- Pre-event features may include proximity, expected importance, consensus/estimate values when point-in-time valid, option-implied move, and historical event-family risk; they must not include realized result or realized reaction.

### Unscheduled surprise events

Examples: sudden accident, unexpected lawsuit, regulatory raid, sanctions headline, management resignation, banking stress headline, war escalation, surprise offering, or credible investigative report.

Contract:

- The specific event is invisible before the first credible point-in-time source.
- `event_awareness_time` normally equals the first credible `source_published_time` / `available_time` pair.
- Pre-event modeling may only use background vulnerability/hazard priors from already-visible context, not the specific future headline.
- Evaluation should measure detection latency, evidence quality, first-response risk behavior, and decay/resolution behavior after visibility.

### Scheduled recurring data releases

Examples: CPI, payrolls, retail sales, FOMC statement/rate decision, Treasury auctions, inventory reports, and other recurring official calendars.

Contract:

- The shell and scheduled time are known before release.
- Actual/consensus/previous/revision fields must remain separated.
- Surprise-vs-consensus and revision effects are only valid after the release artifact is visible.
- News recaps that merely describe the official release should be canonical-covered by the official release row; independent Fed-path/policy repricing narrative can be a residual if evidence supports it.

### Multi-stage developing events

Examples: investigations, lawsuits, M&A, bankruptcy/restructuring, policy negotiations, geopolitical escalation, and regulatory review.

Contract:

- Preserve each material update as its own point-in-time stage row or detail artifact.
- Do not collapse the entire arc into the first headline or the final resolution.
- Stage transitions should keep previous interpretations immutable and add follow-up/resolution refs rather than overwriting history.

### Golden lifecycle examples

| Family | Lifecycle type | Pre-event usable facts | Result/release facts | Forbidden leakage |
|---|---|---|---|---|
| Earnings | `scheduled_known_outcome_later` | Earnings date/window, consensus if PIT-valid, option-implied move, prior guidance, historical gap risk. | Reported EPS/revenue, beat/miss, guidance, management commentary once released. | Using actual results, call transcript revisions, or post-release price reaction before `available_time`. |
| CPI / macro release | `scheduled_recurring_data_release` | Calendar time, importance, consensus/previous when PIT-valid, background inflation/rates context. | Actual CPI values, revision, surprise-vs-consensus, official release text. | Treating recap news as a new independent CPI fact or using release values before publication. |
| Surprise regulatory raid/news | `unscheduled_surprise` | Only background regulatory vulnerability already visible before the headline. | First credible headline/details and follow-up confirmations after available. | Pretending the specific raid/headline was forecastable; labeling pre-event rows with future facts. |

## Internal model structure

Layer 9 V1 should be auditable and structured before any broad black-box event model. The internal route is:

```text
4A EventEncoder
4B EventContextMatcher
4C EventOverlayScorer
```

### 4A - EventEncoder

Consumes event overview rows and detail artifacts. It answers what the event is before target conditioning.

Typical outputs:

```text
event_base_presence
event_base_intensity
event_base_direction_bias
event_base_uncertainty
event_base_quality
event_native_scope_type
event_lifecycle_state
event_source_reliability
event_revision_risk
event_staleness
```

### 4B - EventContextMatcher

Consumes encoded events plus market, sector, target, mapping, and sensitivity context. It answers whether and how the event matters for this target context.

Typical outputs:

```text
event_target_relevance_score
event_market_relevance_score
event_sector_relevance_score
event_theme_relevance_score
event_context_alignment_score
event_target_sensitivity_score
event_scope_escalation_risk_score
```

### 4C - EventOverlayScorer

Aggregates visible events into horizon-aware `event_risk_intervention / event_context_vector` score families.

Typical scoring heads:

```text
presence_head
timing_proximity_head
intensity_head
direction_bias_head
alignment_head
uncertainty_head
gap_risk_head
reversal_risk_head
liquidity_disruption_head
contagion_risk_head
quality_head
impact_scope_heads
```

## Event scope model

Layer 9 must separate where an event originates from where it may have impact.

### Native scope

`event_native_scope_type` describes where the event comes from:

```text
macro
geopolitical
market_structure
sector
industry
theme
symbol
sec_filing
equity_abnormal_activity
price_action
option_abnormal_activity
unknown
```

Native scope is not enough. An NVDA earnings event is native-symbol but may affect theme, sector, and broad market. A geopolitical event is native-geopolitical but may mostly affect energy, airlines, rates, or defense.

### Impact scope vector

Layer 9 should express impact by score family rather than one enum:

```text
8_event_market_impact_score_<horizon>
8_event_sector_impact_score_<horizon>
8_event_industry_impact_score_<horizon>
8_event_theme_factor_impact_score_<horizon>
8_event_peer_group_impact_score_<horizon>
8_event_symbol_impact_score_<horizon>
8_event_microstructure_impact_score_<horizon>
```

`8_event_dominant_impact_scope_<horizon>` remains useful for audit/debug/routing, but model behavior should primarily depend on the impact score vector.

## Output surface

Conceptual output:

```text
event_risk_intervention / event_context_vector
```

Future physical promoted model-output surface:

```text
trading_model.model_08_event_risk_governor
```

The V1 output should be a point-in-time row keyed by decision context:

```text
available_time
tradeable_time
target_candidate_id | scope_key
market_context_state_ref
sector_context_state_ref
target_context_state_ref
event_risk_intervention / event_context_vector
event_risk_intervention / event_context_vector_ref
score_payload
diagnostics_ref
```

`target_candidate_id` remains opaque. Raw ticker/company identity stays in source/audit/routing metadata outside fitting vectors.

## V1 horizons

Layer 9 V1 uses the same synchronized context horizons unless later evaluation proves a different event-specific grid is needed:

```text
5min
15min
60min
390min
```

## V1 event-context vector score families

V1 uses two score groups: core event risk/quality and impact scope.

### A. Core event risk/quality score families

```text
8_event_presence_score_<horizon>
8_event_timing_proximity_score_<horizon>
8_event_intensity_score_<horizon>
8_event_direction_bias_score_<horizon>
8_event_context_alignment_score_<horizon>
8_event_uncertainty_score_<horizon>
8_event_gap_risk_score_<horizon>
8_event_reversal_risk_score_<horizon>
8_event_liquidity_disruption_score_<horizon>
8_event_contagion_risk_score_<horizon>
8_event_context_quality_score_<horizon>
```

### B. Event impact-scope score families

```text
8_event_market_impact_score_<horizon>
8_event_sector_impact_score_<horizon>
8_event_industry_impact_score_<horizon>
8_event_theme_factor_impact_score_<horizon>
8_event_peer_group_impact_score_<horizon>
8_event_symbol_impact_score_<horizon>
8_event_microstructure_impact_score_<horizon>
8_event_scope_confidence_score_<horizon>
8_event_scope_escalation_risk_score_<horizon>
8_event_target_relevance_score_<horizon>
```

Optional audit/debug field, not a scalar `state_vector_value`:

```text
8_event_dominant_impact_scope_<horizon>
```

V1-full therefore has 21 horizon-aware scalar score families plus one horizon-aware dominant-scope audit field across 4 horizons. V1-minimal may start with the core group only, but impact scope should remain part of the accepted contract because event intensity, event scope, and target relevance are separate semantics.

## Field semantics

| Field type | Range | High value means |
|---|---:|---|
| presence | `[0, 1]` | relevant event presence is higher; not good/bad by itself |
| timing proximity | `[0, 1]` | closer to a sensitive event window |
| intensity | `[0, 1]` | event information shock / attention is stronger |
| direction bias | `[-1, 1]` | positive is target-conditioned positive bias; negative is target-conditioned negative bias |
| alignment | `[-1, 1]` | positive supports current target context; negative conflicts with it |
| uncertainty | `[0, 1]` | information uncertainty is higher; usually worse |
| gap risk | `[0, 1]` | discrete jump/gap risk is higher; high-is-bad |
| reversal risk | `[0, 1]` | current target path is more likely to reverse; high-is-bad |
| liquidity disruption | `[0, 1]` | spread/depth/slippage/liquidity disruption risk is higher; high-is-bad |
| contagion risk | `[0, 1]` | cross-scope transmission risk is higher; high-is-bad |
| context quality | `[0, 1]` | event evidence quality is higher; high-is-good |
| impact score | `[0, 1]` | impact on the named scope is stronger |
| scope confidence | `[0, 1]` | impact-scope classification is more reliable |
| escalation risk | `[0, 1]` | lower-scope event may spread to higher scopes |
| target relevance | `[0, 1]` | event is more relevant to the current target candidate |
| dominant impact scope | enum | audit/debug dominant scope label; model-local, not a scalar score registry value |

## No-event and null policy

No-event windows should not create arbitrary nulls in model-facing core fields.

Default no-event policy:

```text
8_event_presence_score_<horizon> = 0
8_event_timing_proximity_score_<horizon> = 0
8_event_intensity_score_<horizon> = 0
8_event_direction_bias_score_<horizon> = 0
8_event_context_alignment_score_<horizon> = 0
8_event_uncertainty_score_<horizon> = event-driven neutral/baseline
8_event_gap_risk_score_<horizon> = event-driven neutral/baseline
8_event_reversal_risk_score_<horizon> = event-driven neutral/baseline
8_event_liquidity_disruption_score_<horizon> = event-driven neutral/baseline
8_event_contagion_risk_score_<horizon> = event-driven neutral/baseline
8_event_context_quality_score_<horizon> = neutral/high if event coverage is known complete, lower if event coverage is weak
```

Background risk from Layer 1/2/3 must stay distinguishable from event-driven overlay risk. Layer 9 may condition event sensitivity on background state, but should not silently relabel broad market stress as event presence.

## Labels and outcomes

Training/evaluation labels may include future outcomes, but inference features may not.

Evaluation labels can include:

```text
realized_market_move_after_event_<horizon>
realized_sector_move_after_event_<horizon>
realized_industry_move_after_event_<horizon>
realized_theme_move_after_event_<horizon>
realized_peer_group_move_after_event_<horizon>
realized_symbol_move_after_event_<horizon>
realized_correlation_spike_<horizon>
realized_breadth_shift_<horizon>
post_event_gap_realization_<horizon>
post_event_reversal_realization_<horizon>
post_event_volatility_expansion_<horizon>
post_event_liquidity_degradation_<horizon>
post_event_spread_widening_<horizon>
post_event_path_instability_<horizon>
post_event_halt_or_pause_occurrence
target_conditioned_post_event_residual_return_<horizon>
market_adjusted_post_event_return_<horizon>
sector_adjusted_post_event_return_<horizon>
peer_adjusted_post_event_return_<horizon>
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `event_risk_intervention / event_context_vector` at inference time.

## Baselines and validation

Layer 9 should prove incremental value over:

1. no-event baseline: upstream context states only;
2. simple event-count baseline;
3. scheduled-event proximity baseline;
4. residual abnormal-activity-only baseline, excluding bar/liquidity fields already represented in upstream context states;
5. native-scope-only baseline;
6. impact-scope-vector baseline;
7. full EventRiskGovernor / EventRiskGovernor.

Validation should check:

- scope: high market/sector/symbol impact scores correspond to realized impact at those scopes;
- risk: gap/reversal/liquidity/contagion risks correspond to realized post-event path behavior;
- alignment: positive alignment supports current target context more often than negative alignment;
- quality: low-quality/conflicting/revised events are correctly gated or discounted;
- leakage: all feature rows obey `available_time <= decision_time` and artifact revision visibility.

## Boundary rules

Keep these semantics separate:

```text
event presence != event intensity
event intensity != impact scope
impact scope != direction
direction bias != alpha
event risk != trade action
```

Layer 9 must not:

- emit `buy`, `sell`, or `hold`;
- emit alpha confidence, expected residual return, or Layer 5 final adjusted alpha values;
- emit position size or final target exposure;
- choose option contract, strike, DTE, delta, or expression;
- mutate broker/account state;
- use account balance, buying power, PnL, open orders, holdings, or live execution constraints;
- use post-event outcomes, future revisions, or future market paths as inference inputs.

## V1 implementation route

1. **V1.0 event registry and time replay**: preserve `event_id`, `canonical_event_id`, `dedup_status`, `source_priority`, `coverage_reason`, `covered_by_event_id`, category, scope, `available_time`, reference, dedup/revision policy, and point-in-time replay. **Done for local fixture rows.**
2. **V1.1 EventEncoder**: emit presence, timing proximity, intensity, direction bias, uncertainty, and quality. **Done in deterministic scaffold.**
3. **V1.2 context matching**: add target relevance, context alignment, gap/reversal/liquidity/contagion risk. **Done in deterministic scaffold.**
4. **V1.3 impact scope vector**: add market/sector/industry/theme/peer/symbol/microstructure impact, scope confidence, escalation risk, and dominant impact scope. **Done in deterministic scaffold.**
5. **V1.4 evaluation**: compare against no-event, count, proximity, abnormal-activity, native-scope, and impact-scope baselines with walk-forward leakage checks. **Offline label/leakage helpers exist; baseline proof remains promotion work.**
## Final go/no-go judgment — 2026-05-15

The accepted judgment is recorded in `docs/102_event_layer_final_judgment.md`.

Layer 9 is worth building as a bounded EventRiskGovernor / EventIntelligenceOverlay. It is not currently worth promoting as broad event alpha, standalone option abnormality alpha, or a separate `EventActivityBridgeModel`.

Accepted active boundary:

- preserve canonical event timelines, shell/result split, lifecycle clocks, and point-in-time availability;
- consume reviewed event-family interpretations when available;
- use abnormal activity and option flow as provenance, risk, and bridge evidence only unless a family-specific proof clears controls;
- emit risk governance outputs such as uncertainty, review/block/cap/reduce/flatten hints, not broker orders or account mutation.

Current status after the first canonical earnings/guidance scouting pass:

- standalone option abnormality: `deferred_low_signal`;
- strict option abnormality filters: `deferred_low_signal`;
- raw option abnormality plus raw news proximity: `deferred_low_signal`;
- earnings/guidance: `scouting`, with canonical shell/control route proven structurally but still underpowered;
- EventRiskGovernor structural layer: `accepted_architecture`.
