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

## Model-composite construction rule

The model composite should be constructed in this order:
1. assign each timestamp to a discovered state
2. look up the preferred variant/policy for that state
3. apply that state-conditioned choice through time
4. stitch the resulting chosen-variant path into one executable composite series

This is the canonical bridge from unsupervised state discovery to strategy use.

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
