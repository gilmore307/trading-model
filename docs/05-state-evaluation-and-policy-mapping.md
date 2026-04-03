# 05 State Evaluation and Policy Mapping

This document defines **stage 2: attach strategy/oracle outcomes to discovered states, estimate state-conditional winners, and construct routing policy**.

## Stage-2 input

Inputs to stage 2 are:
- discovered states from stage 1
- strategy outputs from `trading-strategy`
- oracle outputs from `trading-strategy`

Stage 2 does not redefine states. It only evaluates and uses them.

## Evaluation protocol

Use a three-window protocol.

### Window A — state fit window
Used only to fit the state model.

### Window B — winner-selection window
Used only to estimate `state -> preferred_variant` mappings.

### Window C — out-of-window evaluation window
Used only to evaluate the stitched composite against baselines and oracle.

This prevents the same slice from being used simultaneously for:
- fitting states
- choosing winners
- claiming out-of-sample effectiveness

## First state-evaluation table shape

The first state-evaluation table should be long-format.

### Key fields
- `research_object_type`
- `symbol`
- `ts`
- `timestamp`
- `month`
- `state_id`
- `family_id`
- `variant_id`

### State-side fields
- `state_id`
- `state_confidence` if available
- layer-presence flags
- minimal state-profile reference if needed

### Strategy-side fields
Use bar-based horizons as the canonical contract:
- `forward_return_1bar`
- `forward_return_3bar`
- `forward_return_12bar`
- `forward_return_24bar`
- `equity`
- `return_since_prev`
- `trade_pnl`
- `position`
- `signal_state` if exposed

### Oracle-side fields
- `family_oracle_selected_variant_id`
- `global_oracle_selected_family_id`
- `global_oracle_selected_variant_id`
- `oracle_forward_return_1bar`
- `oracle_forward_return_3bar`
- `oracle_forward_return_12bar`
- `oracle_forward_return_24bar`
- `oracle_gap_1bar`
- `oracle_gap_3bar`
- `oracle_gap_12bar`
- `oracle_gap_24bar`

Where:
- `oracle_gap_Nbar = oracle_forward_return_Nbar - forward_return_Nbar`

### Primary winner metric

To avoid ambiguity, the default v1 winner metric is explicitly:
- `primary_winner_metric = forward_return_12bar`

And the corresponding oracle comparison field is:
- `primary_oracle_metric = oracle_forward_return_12bar`

If a future experiment uses a different winner metric, it must declare that override explicitly.

## Why long format is preferred

Long format keeps state-conditional variant comparison simple and aligns well with partitioning by:
- `symbol + family + variant + month`

## State -> preferred-variant selection rule (v1 exact definition)

### Step 1 — define monthly excess utility versus default
For each observation `i` that falls in state `s` for variant `v`, define:
- `d_i(s, v) = u_i(v) - u_i(default)`

For v1, define:
- `u_i(v) = forward_return_12bar(v)`
- `u_i(default) = forward_return_12bar(default)`

Then aggregate by month:
- `dbar_{s,v,m} = mean_i d_i(s, v)` over all observations in `(state=s, variant=v, month=m)`

### Step 2 — define monthly summary statistics
For each `(state=s, variant=v)` compute:
- `mu_{s,v}` = mean over months of `dbar_{s,v,m}`
- `sigma_{s,v}` = std over months of `dbar_{s,v,m}`
- `p_{s,v}` = fraction of months where `dbar_{s,v,m} > 0`

### Step 3 — sample-coverage shrinkage
Define:
- `w_{s,v} = min(1, obs_n / N_ref) * min(1, active_months_n / M_ref)`

Recommended v1 defaults:
- `N_ref = 300`
- `M_ref = 6`

### Step 4 — within-state robust standardization
Within the same state, for all eligible variants:
- `z_mu_{s,v} = (mu_{s,v} - median_v'(mu_{s,v'})) / (MAD_v'(mu_{s,v'}) + eps)`
- `z_sigma_{s,v} = (sigma_{s,v} - median_v'(sigma_{s,v'})) / (MAD_v'(sigma_{s,v'}) + eps)`

### Step 5 — first exact winner score
Define:
- `winner_score_{s,v} = w_{s,v} * ( z_mu_{s,v} - 0.5 * z_sigma_{s,v} + 0.5 * (2 * p_{s,v} - 1) )`

## Eligibility gate

A variant is eligible only if:
- `obs_n >= 100`
- `active_months_n >= 3`
- `episode_n >= 5`

## Winner decision rule

For each state:
1. filter to eligible variants
2. compute `winner_score`
3. rank variants by score
4. take top1 and top2

Top1 is accepted only if:
- `winner_score_top1 > 0`
- `winner_score_top1 - winner_score_top2 >= 0.25`
- `p_top1 >= 0.55`

Otherwise emit:
- `no_strong_preference`

## State-winner tie-break cascade

If the score margin between top1 and top2 is below the tie threshold, resolve ties in the following order:
1. larger shrunk monthly excess mean
2. higher positive-month ratio
3. lower monthly dispersion
4. smaller relative oracle gap
5. higher bootstrap winner frequency

If no decisive edge remains, emit:
- `no_strong_preference`

### Oracle-gap role in v1
In v1, oracle gap is:
- not part of the main winner score
- used in reporting
- allowed as a tie-breaker only

## Preferred-variant mapping artifact schema

The routing layer should consume a formal mapping artifact rather than only in-memory rules.

Suggested v1 schema:
- `state_id`
- `winner_type`
- `winner_id`
- `runner_up_id`
- `winner_score`
- `score_margin`
- `selection_confidence`
- `fallback_policy`
- `mapping_version`
- `effective_window_start`
- `effective_window_end`
- `primary_winner_metric`
- `state_model_version`
- `state_label_version`
- `refit_window_id`

## Model-composite stitching rule (v1 defaults)

The goal is to route stably, not to switch on every bar.

### Inputs at each time `t`
From the state model:
- `state_top1 = s1(t)`
- `state_top1_prob = q1(t)`
- `state_top2 = s2(t)`
- `state_top2_prob = q2(t)`
- `state_margin = q1(t) - q2(t)`

From the policy layer:
- `preferred_target = a(s)`

### Gate conditions
A candidate new state must satisfy:
- `q1(t) >= q_min`
- `state_margin >= Delta_q`

Recommended v1 defaults:
- `q_min = 0.60`
- `Delta_q = 0.15`

### Hysteresis rule
Require the same candidate state to satisfy the gates for:
- `H = 3` consecutive bars

### Minimum dwell rule
After switching, keep the current routing target for at least:
- `D = 6` bars

unless a strong-switch override is triggered.

### Strong-switch override
Allow early switching if:
- `q1(t) >= q_strong`
- `state_margin >= Delta_strong`

Recommended v1 defaults:
- `q_strong = 0.80`
- `Delta_strong = 0.30`

### Ambiguous-state fallback
If:
- `preferred_target = none`
- or posterior separation is too weak
- or the current state signal is ambiguous

then do not switch aggressively.
Fallback order:
1. keep current target
2. preferred family
3. global default

### State-level tie-break
If the top two state posteriors are too close:
- prefer keeping the current active state if it still meets minimum confidence
- otherwise mark `ambiguous_state`
- ambiguous state does not trigger routing switches
