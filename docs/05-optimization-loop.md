# 05 Optimization Loop

This repository should improve the model continuously as new data arrives.

## Improvement loop

1. new market/context data arrives from `trading-data`
2. new strategy outputs arrive from `trading-strategy`
3. the aligned learning table is refreshed
4. the unsupervised state model is retrained or updated
5. the model composite is rebuilt from the updated state assignments
6. the model composite is compared against oracle composite and strong fixed baselines
7. weak features / weak separations are identified
8. the representation or clustering setup is improved

## First optimization rule

Before comparing richer layer stacks, the repository should first stabilize the **base-only model path**.

Order of work:
1. make base-only work
2. verify it improves the model composite
3. compare model composite against oracle composite
4. add one optional layer at a time
5. measure whether that layer closes more of the oracle gap

## Primary optimization target

The main optimization target is:
- maximize how much of the oracle composite is captured by the model composite

This is the cleanest expression of model quality.

## Layer-policy optimization

The repository should not assume that every optional layer is always helpful.
It should explicitly test:
- base-only model composite
- base + direct enrichment model composite
- base + direct enrichment + cross-object context model composite

for each research-object type.

That means the optimization loop should answer:
- which layers actually improve model composite quality?
- which layers reduce the gap to oracle composite?
- which layers only add noise?
- which layers help stock objects but not crypto objects?
- which layers are only useful during certain market regimes or time windows?

## Evaluation questions

Each refresh cycle should ask:
- are the discovered states stable over time?
- does the model composite improve over fixed baselines?
- how much oracle gap remains?
- which optional layers add real value?
- can the base-layer-only model still run and remain useful?
- do different research-object types need different context-layer policies?

## Success condition

The model is improving if, over time, it captures a larger share of the oracle composite while remaining usable under partial data availability.
