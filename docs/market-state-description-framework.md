# Market State Description Framework

_Last updated: 2026-03-20_

## Core principle

Dynamic parameters are not the first problem.

The first problem is:
- how to describe the current market state correctly
- how to describe it comprehensively enough that strategy-family performance can be mapped onto it

In other words:
- **market-state description comes before dynamic parameter selection**
- dynamic parameters should be a consequence of market-state understanding, not a guess made in advance

## Why this matters

If market-state description is weak:
- dynamic parameter switching becomes arbitrary
- family comparisons become noisy
- good historical performance may come from luck rather than a stable state/parameter mapping

If market-state description is strong:
- we can ask which family performs best in which state
- we can ask which parameter region performs best in which state
- we can later choose parameters as a function of market state

## Current target

Build a market-state description layer rich enough to support:
1. family-vs-state comparisons
2. parameter-vs-state comparisons
3. weekly review stitching by market-style segments
4. later dynamic parameter selection

## Minimum description dimensions

### 1. Trend strength and direction
Questions:
- is the market trending or not?
- if trending, how strong?
- is the trend persistent or fading?
- what is the directionality quality?

### 2. Volatility state
Questions:
- is volatility high or low?
- is volatility expanding or contracting?
- is the move smooth or shock-like?

### 3. Range / mean-reversion tendency
Questions:
- is price oscillating around a center?
- is range behavior dominating?
- are breakouts failing often?

### 4. Activity / participation quality
Questions:
- is the market active enough to trust signals?
- is the move supported by participation?
- are candles behaving with healthy structure or noisy spikes?

### 5. Structural position
Questions:
- where is price relative to recent ranges?
- is price near breakout boundaries?
- is price highly stretched from a local mean?

## Research usage

The immediate use of these descriptions is not to create a final classifier label.

The immediate use is to answer:
- when does MA family work better?
- when does Donchian family work better?
- when does Bollinger/RSI family work better?
- which parameter region inside one family works better in each state?

## Dynamic-parameter mapping logic

The desired eventual flow is:

1. describe market state
2. map state -> suitable strategy family
3. map state -> suitable parameter region inside that family
4. run the selected dynamic strategy form

So the sequence is:
- **state first**
- **parameter choice second**

## Current implementation direction

The state-description layer should start as a feature system, not as a prematurely rigid label system.

That means first building:
- feature inventory
- feature calculation rules
- feature snapshots aligned to 1-minute history
- state slices or clusters derived from those features

Only after that should stronger labeling or classifier logic become central.

## Near-term task meaning

The next historical research steps should therefore run in parallel:
1. strategy-family baseline buildout
2. market-state feature/description buildout

The project should avoid optimizing dynamic parameters in isolation before the state-description layer is good enough.
