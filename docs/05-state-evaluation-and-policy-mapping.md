# 05 Optimization Loop

This repository should improve the model continuously as new data arrives.

## Two loops, not one

### Loop A — improve state discovery
Questions:
- are the discovered states stable?
- are they recurring?
- do they remain statistically separable over time?

Inputs:
- market-side data only

### Loop B — improve strategy-state mapping
Questions:
- does the model composite improve over fixed baselines?
- how much oracle gap remains?
- which states support which strategy choices?

Inputs:
- discovered states
- strategy outputs
- oracle outputs

## Order of work

1. make the state-discovery step clean and stable
2. choose `k` using usability and stability rather than one geometric metric
3. verify the discovered states recur
4. attach strategy/oracle outcomes
5. build state-conditional policy mapping
6. build the model composite
7. measure model composite versus oracle composite
8. improve features and clustering if the oracle gap remains too large

## State -> preferred-variant selection rule (v1 exact definition)

After the state-evaluation table is built, estimate a preferred variant within each state.

### Step 1 — define monthly excess utility versus default
For each observation `i` that falls in state `s` for variant `v`, define:
- `d_i(s, v) = u_i(v) - u_i(default)`

Where:
- `u_i(v)` is the realized utility of variant `v` on that observation
- `u_i(default)` is the realized utility of the default baseline policy on the same observation

Then aggregate by month:
- `dbar_{s,v,m} = mean_i d_i(s, v)` for all observations in `(state=s, variant=v, month=m)`

### Step 2 — define monthly summary statistics
For each `(state=s, variant=v)` compute:
- `mu_{s,v}` = mean over months of `dbar_{s,v,m}`
- `sigma_{s,v}` = std over months of `dbar_{s,v,m}`
- `p_{s,v}` = fraction of months where `dbar_{s,v,m} > 0`

These are month-level stability statistics, not event-level statistics.

### Step 3 — sample-coverage shrinkage
Define:
- `w_{s,v} = min(1, obs_n / N_ref) * min(1, active_months_n / M_ref)`

Recommended v1 defaults:
- `N_ref = 300`
- `M_ref = 6`

This penalizes variants that look good only because they have too few observations or too little month coverage.

### Step 4 — within-state robust standardization
Within the same state, for all eligible variants, define:
- `z_mu_{s,v} = (mu_{s,v} - median_v'(mu_{s,v'})) / (MAD_v'(mu_{s,v'}) + eps)`
- `z_sigma_{s,v} = (sigma_{s,v} - median_v'(sigma_{s,v'})) / (MAD_v'(sigma_{s,v'}) + eps)`

Interpretation:
- larger `z_mu` is better
- larger `z_sigma` means worse instability, so it should be penalized

### Step 5 — first exact winner score
Define:
- `winner_score_{s,v} = w_{s,v} * ( z_mu_{s,v} - 0.5 * z_sigma_{s,v} + 0.5 * (2 * p_{s,v} - 1) )`

This score favors:
- better monthly excess over default
- more stable cross-month behavior
- higher positive-month ratio
- broader sample and month coverage

## Eligibility gate

A variant is eligible for state-winner competition only if:
- `obs_n >= 100`
- `active_months_n >= 3`
- `episode_n >= 5`

If a variant fails the gate, it is excluded from winner competition for that state.

## Winner decision rule

For each state:
1. filter to eligible variants
2. compute `winner_score`
3. rank variants by score
4. take top1 and top2

Top1 is accepted as the state winner only if all of the following hold:
- `winner_score_top1 > 0`
- `winner_score_top1 - winner_score_top2 >= 0.25`
- `p_top1 >= 0.55`

Otherwise output:
- `no_strong_preference`

## State-winner tie-break rule

If the score margin between top1 and top2 is below the tie threshold, resolve ties in the following order:
1. larger shrunk monthly excess mean
2. higher positive-month ratio
3. lower monthly dispersion
4. smaller relative oracle gap
5. higher bootstrap winner frequency

If no decisive edge remains after all tie-break steps, emit:
- `no_strong_preference`

### Tie threshold
- treat candidates as close when `score_margin < 0.25`

### Tie-break detail

#### Tie-break 1
Compare:
- `shrunk_mu_{s,v} = w_{s,v} * mu_{s,v}`

Higher wins.

#### Tie-break 2
If shrunk means remain too close, compare:
- `p_{s,v}`

Higher positive-month ratio wins.

#### Tie-break 3
If positive-month ratios are still close, compare:
- `sigma_{s,v}`

Lower monthly dispersion wins.

#### Tie-break 4
If still close, compare:
- relative oracle gap

Smaller oracle gap wins.

#### Tie-break 5
If still close, compare:
- `bootstrap_win_freq`

Higher bootstrap winner frequency wins.

## Oracle-gap role in v1

In v1, oracle gap should **not** enter the main winner score directly.

Reason:
The first exact score should first answer the simpler question:
- which variant is the most robust state-conditional switch target relative to default?

So in v1:
- oracle gap is reported separately
- oracle gap is allowed as a tie-breaker when top candidates are very close
- oracle gap does not enter the main score formula yet

## Overfitting rule

The preferred-variant rule must be estimated on a training window and then evaluated out of sample.
Do not choose the winner and score it on the exact same evaluation slice without reporting that it is in-sample.

## Model-composite stitching rule (v1 defaults)

The goal is not to switch routing targets on every bar.
The goal is to route stably using posterior-gated switching with hysteresis and minimum dwell.

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
- confidence gate: `q1(t) >= q_min`
- separation gate: `state_margin >= Delta_q`

Recommended v1 defaults:
- `q_min = 0.60`
- `Delta_q = 0.15`

### Hysteresis rule
Even after passing gates, do not switch immediately.
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

## Oracle-gap report shape

The oracle-gap report should answer:
- where the gap is large
- whether the gap is stable or episodic
- whether routing is reducing the gap

### Section A — overall gap summary
Include:
- `overall_realized_metric`
- `overall_oracle_metric`
- `overall_gap_abs`
- `overall_gap_rel`
- `overall_gap_closure_pct`

Compare at least:
- `global_default`
- `state_routed_composite`
- `oracle_composite`

### Section B — by-month gap panel
One row per month, including:
- `month`
- `realized_metric_default`
- `realized_metric_state_routed`
- `oracle_metric`
- `gap_abs_default`
- `gap_abs_state_routed`
- `gap_closure_pct_default`
- `gap_closure_pct_state_routed`
- `delta_gap_closure_pct`

### Section C — by-state gap table
One row per state, including:
- `state_id`
- `state_support_n`
- `state_support_pct`
- `oracle_metric_mean`
- `realized_metric_mean`
- `gap_abs`
- `gap_rel`
- `gap_rank`
- `gap_by_month_std`
- `positive_gap_month_ratio`
- `preferred_target`
- `post_routing_realized_metric`
- `post_routing_gap_abs`
- `gap_reduction_abs`
- `gap_reduction_pct`
- `actionability_tag`

Suggested tags:
- `improvement_opportunity`
- `already_well_captured`
- `structurally_hard`
- `uncertain`

### Section D — by-family / by-parameter-region gap panel
One row per family or parameter region, including:
- `family_id` or `param_region`
- `support_n`
- `oracle_metric_mean`
- `realized_metric_mean`
- `gap_abs`
- `gap_rel`
- `best_states`
- `worst_states`
- `state_concentration_of_gap`

Support `state x family` or `state x param_region` slicing as secondary views when support is sufficient.

## Stage-1 expansion order

The discovery step should expand in this order:
1. base-only price/volume features
2. microstructure features
3. derivatives-context features
4. news/options features
5. structural / cross-object context features

Only move to the next layer after the previous layer's effect on state quality is understood.

## Stage-2 optimization target

The main stage-2 optimization target is:
- maximize how much of the oracle composite is captured by the model composite

But that optimization must happen **after** a clean state-discovery step, not by leaking strategy outcomes into clustering.
