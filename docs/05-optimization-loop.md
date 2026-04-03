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
