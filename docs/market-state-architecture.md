# Market-State Architecture

_Last updated: 2026-03-20_

## Core design decision

The project should not be built as a single model that directly outputs one "best strategy id".

The target system is a **conditional strategy allocation system**:

**market-state layer -> conditional performance layer -> real-time selector**

This means the system should answer:
- what kind of market state is present now
- which strategy family is conditionally strongest in that state
- which parameter region is conditionally strongest inside that family
- whether switching is worth the cost right now

## Optimization target

The center of the system is not raw regime-label accuracy.

The real object to estimate is a conditional utility surface:

`U(strategy_family, parameter_vector | market_state_features_at_t)`

Where utility should include more than gross return.

Preferred utility components:
- forward return over horizon `H`
- drawdown penalty
- turnover penalty
- switching-cost penalty
- optional liquidity/slippage penalty

The practical goal is:
- do not merely classify the market
- estimate whether market-state representation creates useful separation in downstream strategy/parameter performance

## Layer 1 — Market-State Encoder

Inputs:
- normalized market features from current and trailing windows
- multi-timescale price, volatility, participation, and derivatives-context features

Outputs:
1. state probabilities
2. continuous market-state embedding
3. transition / instability score

### Why probabilistic output matters

Real markets often sit in transition bands.
Hard regime labels are too brittle for direct strategy switching.

The encoder should therefore expose:
- main state probability
- second-best state probability
- entropy / uncertainty proxy
- transition score / instability score

### Recommended implementation order

#### v1
- feature engineering first
- descriptive slicing / clustering / simple latent-state experiments
- no heavy commitment to one model class yet

#### v2
- HMM / Markov-switching models on top of improved feature inventory
- evaluate whether latent states actually separate family/parameter performance

#### v3
- richer encoder that outputs both latent probabilities and continuous embedding for downstream scorers

## Layer 2 — Strategy Family Scorer

This layer should decide which **family** deserves attention before choosing exact parameters.

Examples of family-level outputs:
- trend-following family score
- mean-reversion family score
- breakout family score
- volatility-expansion family score

Form:
- `Score_family(s | x_t, z_t)`

Where:
- `x_t` = current feature vector
- `z_t` = latent-state probabilities / embedding from layer 1

### Design rule

Do not flatten all strategies and all parameter combinations into one huge classification problem.

First choose among families.
Then choose parameters inside the selected family.

## Layer 3 — Parameter Surface Model

Inside a family, parameters should be treated as a structured vector, not as unrelated ids.

The objective is to learn:
- `U(theta | family, x_t, z_t)`

For example in MA family:
- fast window
- slow window
- entry threshold
- exit threshold
- MA type
- price source

This turns the problem into learning a parameter-performance surface conditioned on market state.

### Why this matters

If every parameter combination is treated as a separate label:
- the action space explodes
- data becomes sparse
- the system learns ids instead of structure

A parameter-surface model lets the project learn how performance moves as parameters move.

## Layer 4 — Real-Time Selector

The selector should choose the deployed family/parameter pair only after adjusting for constraints.

Preferred decision form:

`argmax expected_utility - risk_penalty - switch_cost - turnover_penalty`

### Required guardrails

The selector should not switch aggressively just because a new option looks slightly better on paper.

Required controls:
- confidence threshold on state quality
- minimum advantage threshold before switching
- cooldown / minimum hold window
- transition-state protection when market is unstable

## Offline research outputs required

Before live selection, the project should produce a reusable offline research object:

**State x Strategy Family x Parameter Region**

Each cell should contain at least:
- average return
- drawdown
- Sharpe / Sortino if useful
- win rate
- turnover
- average holding time
- cost sensitivity

This object should become a first-class dashboard artifact.

Presentation rule:
- do not create one page per tiny strategy variant by default
- use family-level pages first
- drill down by parameter dimensions / parameter regions when needed
- for MA, the family page should summarize all MA variants together; the next layer should be parameter-centric rather than variant-centric

## Training-data construction rule

Training data should not be:
- `X -> best strategy id`

Training data should instead be built as:
- `(market features, state representation, family id, parameter vector) -> future utility`

For each timestamp `t`, generate candidate rows for each family/parameter configuration under consideration.

This keeps the problem aligned with conditional utility estimation rather than noisy label guessing.

## Validation rule

Use only time-ordered validation.

Required:
- rolling or expanding walk-forward evaluation
- state encoder fit only on data available up to that point
- conditional performance models fit only on past data
- out-of-sample aggregation across windows

Never build latent states using full-sample future knowledge and then backfill them into the past as if they were live-known.

## Recommended implementation order for this project

### Phase A — groundwork
1. define market-state feature inventory
2. complete historical data acquisition for first-wave data types
3. normalize datasets into consistent storage and schemas
4. produce first descriptive state slices

### Phase B — conditional research
1. run family baselines on historical data
2. build state x family x parameter-region performance cube
3. identify useful family-state separations
4. eliminate dominated families/regions early

### Phase C — latent-state modeling
1. add HMM / Markov-switching experiments
2. compare latent-state usefulness against simpler descriptive slices
3. keep only state models that improve downstream conditional separation

### Phase D — selector
1. build family scorer
2. build family-internal parameter surface models
3. add switching-cost-aware selector
4. test with walk-forward evaluation before any live promotion

## Immediate project implication

The project priority is no longer just:
- implement more strategies

It is now:
- build enough market-state data and feature coverage to support conditional strategy allocation

That means market-state data and feature work is now on the critical path for family optimization and dashboard design.
