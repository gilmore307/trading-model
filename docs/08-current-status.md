# 08 Current Status

## Current state

The repository has been intentionally stripped down so the old hybrid implementation does not keep leaking outdated assumptions into the new design.

At this stage, the docs are the source of truth.

## Current design commitment

This repository will be rebuilt around one clear line:
- use `trading-data` to discover market states
- use `trading-strategy` only after state discovery to evaluate and map policies
- build an unsupervised market-state model first
- build strategy-state mapping second

## Current evaluation commitment

The primary evaluation logic is now explicit:
- first discover states from market data alone
- then build a long-format state-evaluation table
- then estimate state -> preferred-variant mappings
- then build a model composite from those mappings
- compare the model composite against the oracle composite
- treat the oracle gap as the main model-quality signal

## Current stage-2 commitment

The v1 defaults are now explicitly defined for:
- state-winner score
- state-winner tie-break cascade
- posterior-gated stitching with hysteresis and dwell rules
- four-layer oracle-gap reporting

## What comes next

The next remaining design work is mostly threshold calibration and implementation detail, not basic conceptual structure.

## Implementation progress update

A new minimal implementation skeleton now exists under `src/trading_model/`.

What is already wired:
- market bar loading from `trading-data/data/<symbol>/<month>/bars_1min.jsonl`
- base-only v1 feature construction for stage 1
- winsorization + robust scaling before clustering
- candidate-`k` model selection for GMM/KMeans
- state-table generation with confidence fields
- first-pass stability report generation
- variant return loading from `trading-strategy/data/<symbol>/<family>/<variant>/<month>/returns.jsonl`
- global-oracle return loading from `trading-strategy/data/<symbol>/global_oracle/global_oracle/<month>/returns.jsonl`
- state-evaluation table construction
- first winner-mapping artifact generation
- first oracle-gap report generation

What is still intentionally rough:
- attach-status logic currently distinguishes only basic missing/non-missing cases and should be tightened to exact-vs-previous-bar audit fidelity
- strategy-side forward-horizon fields still need alignment with richer upstream strategy artifacts instead of only the current first-pass fields
- oracle-gap reporting is still a compact v1 report, not the full four-layer report contract
- the model-selection/stability logic is still heuristic and has not yet implemented the exact threshold/calibration policy promised in docs
