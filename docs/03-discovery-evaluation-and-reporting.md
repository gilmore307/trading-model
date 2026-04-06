# 03 Discovery, Evaluation, and Reporting

This document defines stage-1 discovery, stage-2 evaluation/policy mapping, and the main reporting/output logic.

## Stage 1 — Unsupervised discovery

Objective:
- discover recurring market-state structure from market data itself
- avoid strategy outcomes contaminating state definition

### Hard boundary
Stage 1 may use market-descriptive information from `trading-data`, but it must not use:
- strategy returns
- oracle labels
- variant success statistics
- downstream policy information

### Time-causality rule
At time `t`, every discovery feature may use only data from `[t-w+1, t]`.

### First base-only feature set
Current v1 includes:
- return features
- realized-volatility features
- range-width features
- relative-activity features
- trend-slope features
- directionality features

### First clustering family
- primary model: GMM
- baseline model: KMeans

### State-assignment confidence fields
Current discovery artifacts expose two related but different state-assignment diagnostics:
- `state_confidence`
  - the top-1 posterior assignment strength for the selected state
  - under GMM this is the highest posterior probability among candidate states
- `state_margin`
  - the separation between the top-1 and top-2 candidate states
  - interpreted as assignment clarity rather than absolute probability

Interpretation rule of thumb:
- high confidence + high margin -> clean state assignment
- moderate confidence + low margin -> assignment exists but is near a state boundary
- low/flat confidence + low margin -> ambiguous regime labeling

For clustering families that do not naturally expose posterior probabilities, these fields may be null until a compatible approximation is added.

### Cluster-count selection rule
Use candidate `k` values such as `{4, 6, 8, 10, 12}` and choose the smallest `k` that already yields stable and useful state separation.

## Stage 2 — State evaluation and policy mapping

Inputs:
- discovered states from stage 1
- strategy outputs from `trading-strategy`
- oracle outputs from `trading-strategy`

Stage 2 does not redefine states. It only evaluates and uses them.

### Evaluation protocol
Use a three-window protocol:
- Window A — state fit window
- Window B — winner-selection window
- Window C — out-of-window evaluation window

### Two-table split

#### State table
Keyed by:
- `symbol`
- `ts`

Contains market-only or market-descriptive state features plus discovered assignments.

#### State-evaluation table
Keyed by:
- `symbol`
- `ts`
- `family_id`
- `variant_id`

Contains discovered state ids plus strategy/oracle outcomes aligned to those states.

Current attach audit fields now explicitly include:
- `attach_status`
- `attach_delta_ms`
- `attach_abs_delta_ms`
- `attach_tolerance_ms`
- `attach_match_direction`
- `oracle_attach_status`
- `oracle_attach_delta_ms`
- `oracle_attach_abs_delta_ms`
- `oracle_attach_tolerance_ms`
- `oracle_attach_match_direction`

Interpretation:
- `exact` = timestamps match exactly
- `previous_bar` = backward asof match within tolerance
- `out_of_tolerance` = a match existed but falls outside the tolerated lag or implies an invalid forward match
- `missing` = no usable upstream match was attached

### Winner-selection rule
Current v1 explicitly defines:
- primary winner metric
- winner score
- eligibility gate
- winner decision rule
- tie-break cascade

### Model-composite stitching rule
Current v1 explicitly defines:
- posterior confidence gates
- hysteresis
- minimum dwell
- strong-switch override
- ambiguous-state fallback

### Execution-facing confidence contract
Current v1 now exposes a first standardized downstream-facing confidence field on state-to-variant judgments.

Contract:
- field name: `execution_confidence`
- numeric range: `[0.0, 1.0]`
- semantics: ranking strength for a state-routed variant selection, not calibrated fill probability
- current construction combines:
  - winner-selection positive-month ratio
  - score-margin strength over the runner-up
  - eligible-choice coverage depth
- non-variant / blocked states must emit `0.0`
- companion fields may include:
  - `opportunity_strength`
  - `execution_confidence_bucket`
  - `execution_confidence_contract`
  - `execution_confidence_semantics`

This contract is intended to be comparable enough for first-stage downstream sizing/routing experiments while remaining explicitly heuristic until later calibration work is complete.

## Reporting and output boundary

Core output types include:
- market-only state tables
- state-evaluation tables
- unsupervised state-model artifacts
- state -> preferred-variant mappings
- model composite outputs
- oracle-comparison reports
- baseline comparisons

### Primary evaluation output
The main scorecard is the comparison between:
- model composite
- oracle composite

### Required comparison baselines
Also include at least one simple baseline such as:
- volatility quantile bucket baseline
- return-vol 2D bucket baseline

### Refresh / versioning contract
Track at least:
- `state_model_version`
- `state_label_version`
- `mapping_version`
- `refit_window_id`

Also maintain matching artifacts for old -> new state identity where needed.
