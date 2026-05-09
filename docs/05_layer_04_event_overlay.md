# Layer 04 - EventOverlayModel

Status: accepted Layer 4 design route; deterministic V1 scaffold implemented in `src/models/model_04_event_overlay/`.

## Purpose

`EventOverlayModel` is Layer 4. It converts point-in-time visible event evidence into an `event_context_vector` for the current market, sector, and target context.

Layer 4 answers:

- Which events are visible at this decision time?
- Are those events macro, sector, industry, theme, peer-group, symbol, or microstructure scoped?
- How relevant is each event to the current anonymous target candidate?
- Does the event support or conflict with the current `target_context_state`?
- Does the event raise uncertainty, gap risk, reversal risk, liquidity-disruption risk, or contagion risk?
- How reliable, fresh, complete, and conflict-free is the event evidence?

Layer 4 does **not** answer alpha, trade, expression, sizing, or execution questions. It must not emit buy/sell/hold, final action, position size, option contract, strike, DTE, delta, order instruction, or account-specific decision fields.

## Position and input chain

Layer 4 is an event-context overlay on top of the accepted state stack:

```text
market_context_state
+ sector_context_state
+ target_context_state
+ source_04_event_overlay
+ event_detail_artifacts
+ scope_mapping_metadata
+ sensitivity_metadata
  -> EventOverlayModel
  -> event_context_vector
```

The upstream states are reviewed context inputs, not raw feature shortcuts. Layer 4 may use ticker/symbol identity for event matching, routing, and audit, but model-facing fitting vectors must keep raw ticker/company identity outside the payload.

## Inputs

Production inference inputs must be point-in-time only:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_context_state_ref
source_04_event_overlay rows visible by available_time
canonical-event and dedup metadata visible by available_time
event_detail_artifact references visible by available_time
scope_mapping_metadata visible by available_time
sensitivity_metadata visible by available_time
```

### Input A - `source_04_event_overlay`

`trading-data` owns the current one-row-per-event overview table:

```text
source_04_event_overlay
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
- equity abnormal activity artifact: abnormal return, volume, dollar volume, spread, volatility, gap, liquidity, range expansion, VWAP-deviation evidence, and price-action event tokens such as false breakout, failed breakdown, liquidity sweep, bull trap, or bear trap;
- price-action artifact: prior range high/low, breakout or breakdown excursion, close-back-inside evidence, upper/lower wick rejection, sweep/trap token, and detector threshold metadata;
- option abnormal activity artifact: IV shock, skew change, term-structure shift, unusual volume, call/put imbalance, large trade, sweep/block indicators, OI change, option liquidity, spread widening, and dealer-flow context when reviewed.

Artifacts must remain point-in-time versioned. A later article revision, later SEC interpretation, or post-event price reaction can be a training/evaluation label only; it cannot be an inference feature.

### Input C - upstream context states

Layer 4 consumes slim, reviewed state/context outputs:

```text
market_context_state_ref
sector_context_state_ref
target_context_state_ref
```

The relevant state information includes broad market risk/stability/liquidity context, sector trend/stability/liquidity/handoff context, and target direction/trend/path/noise/transition/liquidity/tradability context. Layer 4 uses these to decide whether an event is amplified, dampened, aligned, conflicting, or irrelevant for the current target.

### Input D - scope mapping and sensitivity metadata

Layer 4 needs mapping metadata for event-to-target relevance:

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

Layer 4 is a high-leakage-risk layer. The primary visibility rule is:

```text
event_visible := event.available_time <= decision_available_time
```

Do not replace this with `event_time <= decision_time`. Scheduled future events can be visible before they happen; revised articles can become visible after the original article; detector rows can be generated after the bar window closes.

Recommended event clocks:

```text
event_scheduled_time
event_effective_time
event_actual_time
source_published_time
source_updated_time
ingested_time
available_time
decision_time
tradeable_time
```

Recommended lifecycle states:

```text
scheduled_future
pre_event_window
live_release_window
post_event_initial_reaction
post_event_decay
stale_event
unknown
```

Training/evaluation datasets may include realized future outcomes as labels. Inference rows and `event_context_vector` must not include post-event outcomes, hindsight event interpretations, future source revisions, or future price/option paths.

## Internal model structure

Layer 4 V1 should be auditable and structured before any broad black-box event model. The internal route is:

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

Aggregates visible events into horizon-aware `event_context_vector` score families.

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

Layer 4 must separate where an event originates from where it may have impact.

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

Layer 4 should express impact by score family rather than one enum:

```text
4_event_market_impact_score_<horizon>
4_event_sector_impact_score_<horizon>
4_event_industry_impact_score_<horizon>
4_event_theme_factor_impact_score_<horizon>
4_event_peer_group_impact_score_<horizon>
4_event_symbol_impact_score_<horizon>
4_event_microstructure_impact_score_<horizon>
```

`4_event_dominant_impact_scope_<horizon>` remains useful for audit/debug/routing, but model behavior should primarily depend on the impact score vector.

## Output surface

Conceptual output:

```text
event_context_vector
```

Future physical promoted model-output surface:

```text
trading_model.model_04_event_overlay
```

The V1 output should be a point-in-time row keyed by decision context:

```text
available_time
tradeable_time
target_candidate_id | scope_key
market_context_state_ref
sector_context_state_ref
target_context_state_ref
event_context_vector
event_context_vector_ref
score_payload
diagnostics_ref
```

`target_candidate_id` remains opaque. Raw ticker/company identity stays in source/audit/routing metadata outside fitting vectors.

## V1 horizons

Layer 4 V1 uses the same synchronized context horizons unless later evaluation proves a different event-specific grid is needed:

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
4_event_presence_score_<horizon>
4_event_timing_proximity_score_<horizon>
4_event_intensity_score_<horizon>
4_event_direction_bias_score_<horizon>
4_event_context_alignment_score_<horizon>
4_event_uncertainty_score_<horizon>
4_event_gap_risk_score_<horizon>
4_event_reversal_risk_score_<horizon>
4_event_liquidity_disruption_score_<horizon>
4_event_contagion_risk_score_<horizon>
4_event_context_quality_score_<horizon>
```

### B. Event impact-scope score families

```text
4_event_market_impact_score_<horizon>
4_event_sector_impact_score_<horizon>
4_event_industry_impact_score_<horizon>
4_event_theme_factor_impact_score_<horizon>
4_event_peer_group_impact_score_<horizon>
4_event_symbol_impact_score_<horizon>
4_event_microstructure_impact_score_<horizon>
4_event_scope_confidence_score_<horizon>
4_event_scope_escalation_risk_score_<horizon>
4_event_target_relevance_score_<horizon>
```

Optional audit/debug field, not a scalar `state_vector_value`:

```text
4_event_dominant_impact_scope_<horizon>
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
4_event_presence_score_<horizon> = 0
4_event_timing_proximity_score_<horizon> = 0
4_event_intensity_score_<horizon> = 0
4_event_direction_bias_score_<horizon> = 0
4_event_context_alignment_score_<horizon> = 0
4_event_uncertainty_score_<horizon> = event-driven neutral/baseline
4_event_gap_risk_score_<horizon> = event-driven neutral/baseline
4_event_reversal_risk_score_<horizon> = event-driven neutral/baseline
4_event_liquidity_disruption_score_<horizon> = event-driven neutral/baseline
4_event_contagion_risk_score_<horizon> = event-driven neutral/baseline
4_event_context_quality_score_<horizon> = neutral/high if event coverage is known complete, lower if event coverage is weak
```

Background risk from Layer 1/2/3 must stay distinguishable from event-driven overlay risk. Layer 4 may condition event sensitivity on background state, but should not silently relabel broad market stress as event presence.

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

Labels must be materialized only in training/evaluation datasets and must not be joined into `event_context_vector` at inference time.

## Baselines and validation

Layer 4 should prove incremental value over:

1. no-event baseline: upstream context states only;
2. simple event-count baseline;
3. scheduled-event proximity baseline;
4. abnormal-activity-only baseline;
5. native-scope-only baseline;
6. impact-scope-vector baseline;
7. full EventOverlayModel.

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

Layer 4 must not:

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
