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

## State -> preferred-variant selection rule

After the state-evaluation table is built, estimate a preferred variant within each state.

### Core rule
The preferred variant for a state should not be chosen by a single lucky outcome.
It should be chosen by a state-conditional score that balances:
- average utility / return
- robustness / stability
- sufficient sample count

### First practical rule
For each `(state_id, family_id, variant_id)` group, compute at least:
- sample count
- mean forward return / utility
- positive-rate
- dispersion / volatility of outcome
- oracle-gap summary if available

Then define a ranking score that rewards:
- higher conditional utility
- better consistency
- enough observations to trust the estimate

### Minimum sample rule
A variant should not be eligible as the preferred winner of a state unless it has enough observations in that state.

If no variant meets the minimum sample rule, fall back to:
- family-level winner
- or broader baseline policy
- but never a thin-sample lucky winner

### Overfitting rule
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
