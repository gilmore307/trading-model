# 19 Strategy Library Boundary

_Last updated: 2026-04-03_

This document defines the proposed split boundary for extracting strategy family / variant ownership into a dedicated repository.

## Why split this now

After the upstream data-acquisition layer moved to `trading-data`, the remaining size/complexity pressure inside `trading-model` is no longer mostly about source adapters.
It is increasingly about mixing together two different responsibilities:

1. **research orchestration / evaluation**
2. **strategy family system definition**

The strategy family / variant layer has its own domain model, lifecycle, and artifact rules.
That makes it a strong candidate for a dedicated repository.

## Proposed new repository role

Working description:
- a dedicated **strategy-definition and strategy-family systems** repository

Suggested working names to evaluate:
- `trading-strategy`
- `strategy-model`
- `trading-family`

Current recommendation:
- `trading-strategy`

Reason:
- it is broad enough to hold family/variant definitions without sounding tied only to one modeling method
- it reads clearly alongside `trading-data`, `trading-model`, and `quantitative-trading`

## Proposed architecture after split

### `trading-data`
Owns:
- upstream market-data acquisition
- source adapters
- ETF/context acquisition
- monthly market/context handoff artifacts

### `trading-strategy` (new)
Owns:
- strategy family definitions
- variant schema and identity rules
- parameter dimensions and admissible parameter spaces
- family registry
- variant instantiation logic
- family/variant metadata and lifecycle state
- request-driven strategy execution for requested instrument/family/variant payloads
- family/global Oracle construction
- family-level artifact contracts
- standardized partitioned strategy outputs and run manifests

### `trading-model`
Owns:
- market-state / regime modeling
- feature engineering
- research datasets built from upstream handoff data
- backtests and offline evaluation execution
- cross-family comparative research
- model selection / ranking logic
- promotion-candidate generation

### `quantitative-trading`
Owns:
- live execution
- runtime state
- promoted strategy consumption
- live switching / routing / execution fidelity

## Core split rule

The new strategy repository should own the answer to:
- **what strategies exist, how they are structured, how a family expands into variants, and what metadata/constraints define them**

`trading-model` should own the answer to:
- **how those strategies perform on historical data, under which market states, and which ones should be selected or promoted**

That is the cleanest boundary.

## What should move to the new strategy repo

### 1. Family registry and identity layer
Examples:
- family registry
- family ids / variant ids
- canonical naming rules
- parameter-dimension definitions
- variant serialization schema

### 2. Family-specific strategy logic
Examples:
- MA family definition
- Donchian family definition
- Bollinger family definition
- RSI family definition
- MACD family definition
- grid family definition
- future family packs

Important nuance:
- the **strategy logic and parameterization definition** should move
- the **historical evaluation framework that runs them at scale** can stay in `trading-model`

### 3. Variant-generation / parameter-space rules
Examples:
- baseline variant templates
- dynamic-parameter schema
- admissible parameter bounds
- family-specific validation rules
- variant expansion rules for batch research

### 4. Family / variant metadata and lifecycle
Examples:
- `idea`
- `specified`
- `implemented`
- `backtested`
- `reviewed`
- `promoted`
- `rejected`

### 5. Artifact contracts for family/variant definitions
Examples:
- family summary schema
- variant summary schema
- retained-full vs summary-only policy
- family/variant status manifests

## What should stay in `trading-model`

### 1. Research-side data products
- research datasets
- feature tables
- market-state datasets
- regime labels
- evaluation windows and cross-validation structure

### 2. Historical evaluation and comparison
- backtest runners
- comparative evaluation
- family champion selection
- oracle composite analysis
- regime composite analysis
- cross-family ranking
- promotion recommendation logic

### 3. Market-state-conditioned selection logic
This is especially important.

The strategy repo may define that a family supports dynamic parameters or state-conditioned variants.
But `trading-model` should still own:
- market-state description
- state detection
- relevance scoring
- state-aware family selection evaluation

## What should not move into the new strategy repo

To avoid rebuilding another oversized monolith, do **not** make the new strategy repo responsible for:
- upstream market-data acquisition
- market-state feature engineering
- regime clustering
- historical evaluation pipeline orchestration for the whole system
- promotion workflow into live runtime
- live execution logic

## Practical code-boundary rule

### New strategy repo should look like
- `src/families/`
- `src/variants/`
- `src/registry/`
- `src/schema/`
- `src/templates/`
- `docs/` focused on family/variant definitions and contracts

### `trading-model` should keep
- `src/research/`
- `src/features/`
- `src/regimes/`
- `src/pipeline/`
- evaluation/reporting/ranking code

## Interface between `trading-strategy` and `trading-model`

The clean interface should be:

### Strategy-definition outputs from `trading-strategy`
- family definitions
- variant definitions or generators
- parameter schemas
- metadata / status manifests
- artifact schema contracts

### Evaluation inputs consumed by `trading-model`
- variant trade outputs
- variant return/equity outputs
- family Oracle outputs
- global Oracle outputs
- run manifests
- canonical family/variant identifiers and parameter payloads

### Evaluation outputs produced by `trading-model`
- selector/model datasets
- ranking summaries
- Oracle-gap comparisons
- family champion selections
- model-produced composite comparisons
- promotion recommendations

## Recommended first split boundary

Do not try to move every strategy-related thing at once.

### First migration slice
Move first:
- family registry
- MA family definition
- Donchian family definition
- Bollinger family definition
- candidate-pool metadata / lifecycle definitions
- family/variant schema docs

Keep temporarily in `trading-model`:
- research runners
- comparative evaluation scripts
- report builders
- family comparison reports

This gives a low-risk first split.

## Naming decision recommendation

My recommendation is:
- **new repo name: `trading-strategy`**

Because the boundary is really about strategy-definition ownership, not just “family artifacts”.
`family` and `variant` become internal concepts of that repo rather than the repo name itself.

## Final boundary summary

### `trading-data`
Owns **data acquisition**.

### `trading-strategy`
Owns **strategy family/variant definition and parameter-space modeling**.

### `trading-model`
Owns **historical evaluation, market-state modeling, comparison, and selection**.

### `quantitative-trading`
Owns **live execution**.
