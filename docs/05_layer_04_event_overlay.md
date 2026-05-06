# Layer 4 EventOverlayModel

Status: accepted design route; deterministic model implementation pending.

## Purpose

`EventOverlayModel` is Layer 4. It converts point-in-time event evidence into an `event_context_vector` before alpha confidence is estimated.

The model answers:

- What events are visible near this market/sector/target context?
- Are they scheduled, breaking, lagging evidence, or prior-signal abnormal activity?
- Do they increase uncertainty, gap risk, reversal risk, liquidity disruption, or contagion risk?
- Do they support, conflict with, or invalidate the current target context?
- Should the next AlphaConfidenceModel see a clean context, a risk-adjusted context, or a gated/watch context?

Layer 4 does **not** output buy/sell/hold, final action, position size, option contract, strike, DTE, delta, or execution instruction.

## Position in the stack

```text
market_context_state
+ sector_context_state
+ target_context_state
+ source_04_event_overlay / event evidence
  -> EventOverlayModel
  -> event_context_vector

market_context_state
+ sector_context_state
+ target_context_state
+ event_context_vector
  -> AlphaConfidenceModel
  -> alpha_confidence_vector
```

Event modeling happens before alpha confidence because event evidence changes the truth, risk, and tradability of any predicted alpha. A confidence model that does not see event context would be blind to macro releases, earnings, breaking news, SEC filings, abnormal equity activity, and abnormal option activity.

## Inputs

Production inference inputs must be point-in-time only:

```text
available_time
tradeable_time
market_context_state_ref
sector_context_state_ref
target_context_state_ref
source_04_event_overlay rows visible by available_time
optional event detail references
optional historical event-impact memory available by available_time
```

Allowed event evidence includes:

- macro calendar releases and macro news;
- sector news;
- symbol/company news;
- SEC filings;
- earnings or scheduled company events when available through reviewed sources;
- equity abnormal activity events;
- option abnormal activity events;
- halt / limit / market-structure warnings if a reviewed source exists.

The model may use event references, source priority, timestamps, scope, and event category/type. It must not use hindsight interpretation, post-event realized outcome labels, future article revisions, or future price paths as inference features.

## Source surface

`trading-data` owns the current event source surface:

```text
source_04_event_overlay
```

Current SQL overview row fields:

```text
event_id
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

The source intentionally stores one overview row per event. Full news, SEC, macro, detector, and timeline details stay behind `reference` values such as web URLs, SEC file paths, internal artifact paths, or source references.

## Output

Conceptual output:

```text
event_context_vector
```

Future physical model-output surface:

```text
trading_model.model_04_event_overlay
```

The V1 output should be a point-in-time row keyed by the decision context, not by raw event alone:

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

`target_candidate_id` remains an opaque candidate row key. Raw ticker/company identity must stay in audit/routing metadata outside model-facing fitting vectors.

## Event-context vector shape

The primary `event_context_vector` has inspectable blocks:

```text
event_timing_context
event_scope_context
event_type_context
event_intensity_context
event_directional_context
event_risk_context
event_quality_context
```

### `event_timing_context`

Purpose: recency, proximity, and decay.

Example fields:

```text
event_count_<horizon>
latest_event_age_seconds_<horizon>
next_scheduled_event_seconds_<horizon>
pre_event_window_flag_<horizon>
post_event_decay_score_<horizon>
```

### `event_scope_context`

Purpose: map event scope to market, sector, symbol, or anonymous candidate context.

Example fields:

```text
macro_event_count_<horizon>
sector_event_count_<horizon>
symbol_event_count_<horizon>
sector_event_density_score_<horizon>
target_event_density_score_<horizon>
cross_scope_contagion_score_<horizon>
```

### `event_type_context`

Purpose: separate scheduled, news, filing, abnormal-activity, and market-structure evidence.

Example fields:

```text
scheduled_macro_event_score_<horizon>
scheduled_company_event_score_<horizon>
breaking_news_event_score_<horizon>
sec_filing_event_score_<horizon>
equity_abnormal_activity_event_score_<horizon>
option_abnormal_activity_event_score_<horizon>
```

### `event_intensity_context`

Purpose: describe attention/impact magnitude without turning it into trade action.

Example fields:

```text
event_attention_score_<horizon>
event_novelty_score_<horizon>
event_volume_surprise_score_<horizon>
event_price_shock_score_<horizon>
event_option_flow_shock_score_<horizon>
```

### `event_directional_context`

Purpose: capture signed event bias only as context for AlphaConfidenceModel.

Example fields:

```text
event_direction_bias_score_<horizon>   # signed [-1, 1]
event_direction_conflict_score_<horizon>
event_context_alignment_score_<horizon>
```

This block is **not** alpha confidence and not a trading signal.

### `event_risk_context`

Purpose: expose risks that can invalidate or degrade otherwise clean target context.

Example fields:

```text
event_uncertainty_score_<horizon>
event_gap_risk_score_<horizon>
event_reversal_risk_score_<horizon>
event_liquidity_disruption_score_<horizon>
event_volatility_expansion_score_<horizon>
event_halt_or_market_structure_risk_score_<horizon>
event_contagion_risk_score_<horizon>
```

Higher risk scores mean worse/more disruptive context unless a field explicitly says otherwise.

### `event_quality_context`

Purpose: coverage, freshness, source reliability, and conflict diagnostics.

Example fields:

```text
event_coverage_score_<horizon>
event_freshness_score_<horizon>
event_source_reliability_score_<horizon>
event_reference_quality_score_<horizon>
event_conflict_score_<horizon>
```

Quality/diagnostic fields should gate training and inference but should not be mistaken for alpha or action outputs.

## Core score families

V1 core score families use the same horizons as the state/context stack unless a later evaluation proves otherwise:

```text
5min
15min
60min
390min
```

Accepted Layer 4 core score candidates:

```text
4_event_presence_score_<horizon>
4_event_intensity_score_<horizon>
4_event_attention_score_<horizon>
4_event_direction_bias_score_<horizon>
4_event_uncertainty_score_<horizon>
4_event_gap_risk_score_<horizon>
4_event_reversal_risk_score_<horizon>
4_event_liquidity_disruption_score_<horizon>
4_event_contagion_risk_score_<horizon>
4_event_context_quality_score_<horizon>
```

These are event-context scores. They do not choose action, exposure, strategy, or option contracts.

## Labels and outcomes

Training/evaluation labels may include future outcomes, but inference features may not.

Evaluation labels can include:

```text
post_event_return_distribution
post_event_gap_realization
post_event_reversal_realization
post_event_volatility_expansion
post_event_liquidity_degradation
post_event_spread_widening
post_event_path_instability
post_event_halt_or_pause_occurrence
alpha_model_incremental_value_with_event_context
```

Labels must be materialized only in training/evaluation datasets and must not be joined into `event_context_vector` at inference time.

## Baselines

Layer 4 must prove incremental value over:

1. no-event baseline: market + sector + target context only;
2. simple event-count baseline by category/scope;
3. scheduled-event proximity baseline;
4. abnormal-activity-only baseline;
5. full event-context vector.

Promotion should require no leakage, stable walk-forward value, better risk calibration for AlphaConfidenceModel, and clear failure behavior around major event windows.

## Boundaries

Layer 4 may gate or degrade event context for downstream confidence. It must not:

- emit `buy`, `sell`, or `hold`;
- emit position size;
- choose final target exposure;
- choose option contract, strike, DTE, delta, or expression;
- mutate broker/account state;
- use account balance, buying power, PnL, open orders, existing holdings, or live execution constraints;
- use post-event outcomes as inference inputs.
