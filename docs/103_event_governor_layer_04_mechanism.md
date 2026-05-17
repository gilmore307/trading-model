# Event Governor ↔ Layer 4 Mechanism

Status: accepted explanatory contract for the current architecture
Date: 2026-05-17

## Naming note

Current architecture has nine model layers:

```text
Layer 4: EventFailureRiskModel
Layer 8: TradingGuidanceModel / OptionExpressionModel
Layer 9: EventRiskGovernor / EventIntelligenceOverlay
```

Older notes and operator shorthand may refer to the event-governor surface as "Layer 8" because the event layer used to occupy that position before `EventFailureRiskModel` was inserted. In the current route, the precise mechanism is:

```text
Layer 8 base trading guidance
  -> Layer 9 EventRiskGovernor residual/event-risk review
  -> reviewed promotion packet, only when evidence clears gates
  -> Layer 4 EventFailureRiskModel future pre-alpha conditioning
```

This document describes that mechanism. It does not rename Layer 8 or Layer 9.

## Purpose

The event/governor-to-Layer-4 mechanism prevents two failure modes:

1. **late-only event correction:** if a recurring event family reliably breaks a strategy setup, the system should not rediscover the same risk after Layer 8 on every run forever;
2. **circular event alpha:** if a price/liquidity/option anomaly is already represented in Layers 1-8, Layer 9 must not re-score the same data as a new event signal and then promote it upstream.

The accepted solution is two-stage:

- Layer 9 is the discovery, explanation, observation, and risk-intervention surface after base trading guidance.
- Layer 4 is the reviewed pre-alpha conditioning surface for event/strategy-failure relationships that have already proven stable, incremental, point-in-time, and useful.

Layer 9 can propose. Layer 4 can consume only after manager/agent acceptance.

## Layer roles

| Surface | Current role | May do | Must not do |
| --- | --- | --- | --- |
| Layer 8 `TradingGuidanceModel / OptionExpressionModel` | Produces base trading guidance and optional option-expression plan before event-risk overlay. | Emit base action thesis, guidance, option-expression plan/vector, diagnostics, and no-event audit state. | Consume raw event/news residuals as hidden alpha; mutate broker/account state. |
| Layer 9 `EventRiskGovernor / EventIntelligenceOverlay` | Reviews point-in-time event evidence and residual anomalies after base guidance. | Explain, warn, block new entries, cap exposure, require review, nominate reduce/flatten candidates, maintain observation pool, emit Layer 4 promotion packets. | Replace base stack with standalone event alpha; directly send orders; auto-promote event families. |
| Layer 4 `EventFailureRiskModel` | Applies agent-reviewed event/strategy-failure conditioning before alpha confidence. | Output `event_failure_risk_vector`: strategy-failure risk, entry-block pressure, exposure-cap pressure, disable pressure, path-risk amplification, evidence quality, applicability confidence. | Read arbitrary news, unreviewed abnormality, future returns, broker outcomes, or Layer 9 discovery rows without accepted promotion. |

## End-to-end flow

```text
1. Layers 1-8 build the base decision path
   market_context_state
   + sector_context_state
   + target_context_state
   + event_failure_risk_vector when available
   + alpha / position / action / guidance / option-expression outputs
   -> base Layer 8 guidance

2. Layer 9 performs residual/event-risk review
   base Layer 8 guidance
   + source_09_event_risk_governor rows
   + event_detail_artifacts
   + event_interpretation_v1 when available
   + abnormal-activity residual evidence when non-overlap proof exists
   -> event_risk_intervention / event_context_vector

3. Layer 9 classifies the result
   observe / explain / block / cap / reduce / flatten-candidate / human-review
   plus observation-pool and promotion-review evidence where appropriate

4. Promotion packet may be emitted only if evidence clears gates
   family packet + matched controls + split stability + PIT clocks
   + residual/non-overlap proof + leakage review + incremental value evidence

5. Agent/manager review accepts or rejects Layer 4 scope
   accept_layer_04_event_failure_risk_scope
   or defer/reject with reason

6. Future Layer 4 runs consume only the accepted scope
   accepted event family / strategy-failure relationship
   + current PIT context
   -> event_failure_risk_vector before Layer 5 alpha confidence
```

## Startup abnormality scope

Layer 9 may consider abnormal activity only as compact point-in-time detector evidence, provenance, residual explanation, or event-risk context. It is not a standalone alpha source.

Accepted startup abnormality categories:

| Category | Included abnormality examples | Required proof before scoring | Common exclusion |
| --- | --- | --- | --- |
| `price_action_pattern` | false breakout, false breakdown, liquidity sweep high, liquidity sweep low, bull trap, bear trap | compact token with source refs; not raw return/volume/trend reuse | ordinary bar-derived momentum, gap, VWAP, or trend fields already present upstream |
| `residual_market_structure_disturbance` | target-specific unexplained board/tape disturbance after market/sector/peer/target conditioning | `residual_after_upstream_conditioning` proof | anomaly explained by Layer 1-3 context, Layer 5 alpha, Layer 6/7 action state, or Layer 8 guidance |
| `microstructure_liquidity_disruption` | spread widening, depth disappearance, quote-quality breakdown, one-sided prints, halt/pause, anomalous quote environment | outside broad-market and upstream liquidity context | raw spread/liquidity z-score already consumed as a normal liquidity feature |
| `option_derivatives_abnormality` | IV shock, skew/term-structure shock, unusual option volume, call/put imbalance, sweep/block evidence, OI change, option-liquidity disruption | not already consumed by option-expression path, or explicitly residual after that path | option-chain or expression-selection inputs already used by Layer 8 |

Excluded startup scope:

```text
raw_return_zscore_alone
raw_volume_zscore_alone
raw_spread_or_liquidity_zscore_alone
ordinary_equity_bar_fields
ordinary_equity_liquidity_bar_fields
target_state_features
option_expression_inputs
layer_08_guidance_payload_fields
strategy_or_base_stack_failure_labels
post_event_realized_labels
uncalibrated_detector_thresholds_without_review
```

## Non-overlap statuses

Every price, liquidity, or option activity leg must carry one of these statuses for the same decision context:

```text
not_in_upstream_features
residual_after_upstream_conditioning
review_required_overlap_unknown
```

Scoring rule:

| Status | Meaning | Can score/intervene? | Can promote to Layer 4? |
| --- | --- | ---: | ---: |
| `not_in_upstream_features` | Evidence leg is not represented in Layers 1-8 feature/model path. | yes, if other gates pass | possible after full review |
| `residual_after_upstream_conditioning` | Upstream path sees related context, but abnormality remains after conditioning. | yes, if residual proof is accepted | possible after full review |
| `review_required_overlap_unknown` | Overlap is not proven absent. | no; provenance/review only | no |

This is the main anti-circularity rule.

## Event lifecycle type values

Event families must not collapse different timing shapes into one bucket. The lifecycle type changes what the model is allowed to know at inference time.

| Lifecycle type | Meaning | Example | Inference rule |
| --- | --- | --- | --- |
| `scheduled_known_outcome_later` | The event shell is known before the result, but the outcome is not known yet. | earnings date before release; FOMC meeting date before statement | schedule/awareness may be used; result/guidance fields invalid before release availability |
| `unscheduled_surprise` | The event is not specifically visible before first credible publication. | surprise SEC investigation headline; sudden acquisition rumor from credible source | no pre-event event row unless another PIT source existed before publication |
| `scheduled_recurring_data_release` | A recurring macro/data release has known release time and later actual/consensus values. | CPI, payrolls, claims | calendar shell and expectations may be visible; actual/surprise only after release availability |
| `multi_stage_developing_event` | Event evolves through multiple updates, revisions, or resolutions. | war/geopolitical escalation, litigation, regulatory review, M&A process | each update needs its own availability and interpretation timing |
| `unknown` | Timing class cannot be determined safely. | incomplete source evidence | review/provenance only until classified |

## Lifecycle state values

Lifecycle state describes where the current point-in-time row sits in the event arc:

| State | Meaning | Typical allowed use |
| --- | --- | --- |
| `scheduled_future` | Known future shell, no outcome yet. | anticipation/risk calendar context only |
| `pre_event_window` | Before scheduled release/result but close enough to affect positioning/risk. | uncertainty, review, optional exposure caution if accepted |
| `live_release_window` | At or immediately after the information becomes available. | reaction-risk, liquidity/gap-risk, evidence-quality checks |
| `post_event_initial_reaction` | Early absorption/repricing window. | event-risk intervention, path-risk and liquidity stress |
| `post_event_decay` | Event influence is decaying but may still affect volatility/liquidity. | residual risk, stale-event checks |
| `developing_update` | A new update arrives inside a broader event arc. | update-specific interpretation; do not overwrite prior PIT record |
| `resolved` | Outcome/resolution is known. | close prior uncertainty; can become label/evaluation context after availability |
| `stale_event` | Event is too old for current inference except as background context. | audit only unless a reviewed family defines longer persistence |
| `unknown` | State cannot be safely determined. | review/provenance only |

## Required event clocks

Layer 9 and Layer 4 promotion evidence must preserve these clocks when applicable:

| Clock | Meaning | Feature or label? |
| --- | --- | --- |
| `event_awareness_time` | Earliest time the system could know the event shell or existence. | feature if <= decision time |
| `event_scheduled_time` | Scheduled release/meeting/result time. | feature for scheduled events |
| `event_effective_time` | When the event becomes economically/legal effective. | feature if known PIT; otherwise later evidence |
| `event_actual_time` | When the underlying event happened, distinct from publication. | feature only if known PIT |
| `source_published_time` | Provider/source publication timestamp. | feature if source-visible |
| `source_updated_time` | Provider/source revision timestamp. | feature for revision handling |
| `ingested_time` | When local system ingested the source. | audit/availability support |
| `available_time` | Earliest time the model may use the evidence. | hard inference gate |
| `interpretation_time` | When standardized interpretation/review became available. | feature only after this time |
| `resolution_time` | When outcome/resolution became known. | feature only after this time; otherwise label/eval later |
| `decision_time` | Model decision timestamp. | row anchor |
| `tradeable_time` | Earliest realistic trading/action time after decision/availability. | label anchor and action feasibility |
| `reaction_window` | Forward window used to evaluate price/path response. | label/evaluation only, never inference feature |

Hard rule:

```text
feature_time <= available_time <= decision_time <= tradeable_time <= label_window_start
```

Any event fact discovered after `decision_time` is label/evaluation evidence only for that decision row.

## Activity bridge time relation types

`event_activity_bridge` links event evidence to price/liquidity/option/prediction-market activity. Relation type controls whether activity is precursor, reaction, absorption, divergence, or unresolved hazard.

| Relation type | Timing shape | Meaning | Layer 4 promotion implication |
| --- | --- | --- | --- |
| `pre_event_precursor` | activity before public event visibility | Latent hazard increased before canonical source appeared; do not claim the future event was known. | requires strong PIT activity proof, no leakage, and later matched controls before promotion |
| `co_event_reaction` | activity near event visibility | Market/options/liquidity reacted when event became visible. | can support risk/control if reaction is stable and incremental |
| `post_event_absorption` | activity after event visibility | Delayed repricing, disagreement, liquidity stress, or absorption. | may support path-risk/liquidity-risk conditioning |
| `event_activity_divergence` | event and activity disagree | Big event/no reaction, small event/large reaction, odds move/no securities move, or asset move/no news. | usually review/observation first; promotion needs family-specific proof |
| `unresolved_latent_hazard` | activity remains unexplained PIT | No canonical event is visible yet. If later event explains it, add `later_explained` without rewriting history. | cannot promote alone; can seed research/observation |

## Layer 4 promotion packet requirements

A Layer 9 event/abnormality mechanism can become a Layer 4 conditioning factor only if the packet includes:

```text
event_family_key
family_status
accepted_lifecycle_type
accepted_lifecycle_state_rules
required_event_clocks
included_abnormality_categories
excluded_abnormality_categories
source_precedence
point_in_time_availability_proof
upstream_non_overlap_status
residual_after_upstream_conditioning_evidence
matched_controls
forward_label_design
split_stability_evidence
leakage_review
incremental_value_over_base_stack
allowed_layer_04_effects
agent_review_decision
manager_registry_scope
```

Allowed Layer 4 effects are limited to:

```text
observe_only
alpha_conditioning_required
entry_block_recommended
exposure_cap_recommended
strategy_family_disable_recommended
human_review_required
```

Layer 4 still must not emit final buy/sell/hold, select option contracts, size positions, route orders, or mutate broker/account state.

## Practical examples

### Earnings/guidance scheduled shell

- Lifecycle type: `scheduled_known_outcome_later`.
- Useful before result: event shell, expected release time, awareness/scheduled clocks, uncertainty window.
- Not useful before result: actual result, guidance raise/cut, beat/miss, management interpretation.
- Possible Layer 9 role: event-risk calendar warning, uncertainty, review.
- Possible Layer 4 promotion: only after official result/guidance interpretation, expectation baseline, matched controls, and split-stable strategy-failure evidence exist.

### CPI inflation release

- Lifecycle type: `scheduled_recurring_data_release`.
- Useful before release: calendar shell, consensus/forecast if PIT source exists, macro sensitivity.
- Useful after release: actual, surprise, revision, hot/cold classification if PIT available.
- Possible Layer 9 role: volatility/path-risk control, event-day review, macro risk context.
- Possible Layer 4 promotion: only if surprise/risk relationship reliably invalidates a strategy family across controls and regimes.

### Option IV/volume abnormality before news

- Abnormality category: `option_derivatives_abnormality`.
- Bridge relation: `pre_event_precursor` or `unresolved_latent_hazard`.
- Required proof: not already consumed by Layer 8 option-expression path, or residual after that path; no future event leakage; matched no-event/no-abnormality controls.
- Default status: review/provenance unless residual proof and event-family interpretation exist.

### False breakout with no canonical news

- Abnormality category: `price_action_pattern`.
- Bridge relation: `unresolved_latent_hazard`.
- Required proof: compact detector token, source refs, and residual after Layers 1-8 conditioning.
- Default status: residual anomaly discovery; not Layer 4 promotion unless repeated family-level evidence connects it to a reviewed mechanism.

## Summary rule

Layer 9 can say:

```text
"The base Layer 8 guidance is risky because a PIT event or residual abnormality is visible now."
```

Layer 4 can say only after review:

```text
"This accepted event/strategy-failure family should condition alpha before the stack reaches Layer 5."
```

Anything else is either duplicated upstream evidence, unreviewed research, or execution-owned behavior outside `trading-model`.
