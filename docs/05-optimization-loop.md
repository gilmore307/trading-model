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
2. verify the discovered states recur
3. attach strategy/oracle outcomes
4. build state-conditional policy mapping
5. measure model composite versus oracle composite
6. improve features and clustering if the oracle gap remains too large

## First optimization target for stage 1

Before anything else, the repository should optimize for:
- stable recurring states from market data alone

That means the first iteration should focus on:
- compact feature quality
- sensible cluster count
- state stability diagnostics
- transition sanity

Only after that should strategy usefulness become the next loop.

## Primary optimization target for stage 2

The main stage-2 optimization target is:
- maximize how much of the oracle composite is captured by the model composite

But that optimization must happen **after** a clean state-discovery step, not by leaking strategy outcomes into clustering.
