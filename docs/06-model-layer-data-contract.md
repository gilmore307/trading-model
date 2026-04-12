# 06 Model-Layer Data Contract

This document defines the current model-layer decomposition and the intended data-consumption boundary for each model family.

## Core principle

`trading-data` should collect and retain broadly useful upstream information without prematurely deciding which fields are "worth it" for modeling.

`trading-model` consumes those upstream layers through model-specific input contracts.

The same upstream data family may therefore have:
- a **full/raw-ish layer** suitable for specialized downstream models
- a **compressed/context layer** suitable for broader state or strategy models

## Three model families

### 1. Market-state model
Purpose:
- recognize broad market state
- build a view of market regime / sector opportunity / symbol-level context
- help identify unusually favorable sectors, ETFs, or individual symbols

Primary inputs:
- `trading-storage/1_market_regime/*`
- selected `trading-storage/2_market_tape/*` base market features
- optional compressed option-chain context at the underlying-symbol level

Input rule:
- this layer should not ingest full contract-by-contract option chains directly
- derivatives information should enter as compressed underlying-level context

### 2. Strategy-selection model
Purpose:
- take candidate targets and market-state outputs
- choose the most suitable entry / exit strategy style for the selected target

Primary inputs:
- target symbol full market-tape bundle
- upstream market-state outputs
- optional compressed option-chain context for the target underlying

Input rule:
- this layer is still modeling the underlying trade, not the option contract itself
- it may consume option-chain context, but should not depend on raw full-chain tensors as a default requirement

### 3. Option-selection model
Purpose:
- after trade direction / timing is already chosen
- select option parameters that best express the trade while controlling payoff / risk profile

Primary inputs:
- full option-chain layer
- underlying stock/ETF full bundle
- outputs from the market-state and strategy-selection models

Input rule:
- this layer should have access to rich option-chain information rather than only compressed context
- it is the intended consumer of the preserved full option-chain layer

## Option-chain data split

The option data path should support two downstream surfaces at once.

### A. Full option-chain layer
Intended consumer:
- `option_selection_model`

Desired contents:
- option contract / chain metadata
- snapshot-layer context
- Greeks
- implied volatility
- latest trade / latest quote
- open interest and related contract-level metadata
- historical option market data where available

Current confirmed Alpaca options boundary:
- historical option market data is currently confirmed from `2024-02` onward

### B. Compressed option-chain context layer
Intended consumers:
- `market_state_model`
- `strategy_selection_model`

Purpose:
- translate a full option chain into underlying-level explanatory context
- avoid forcing earlier model layers to ingest the full contract graph directly

## First-wave compressed option context

The first compressed option-chain context layer should emphasize underlying-state information rather than contract-level execution optimization.

Recommended first-wave feature groups:
- IV term structure
- skew / downside-vs-upside pricing shape
- open-interest structure
- option volume structure
- liquidity / spread context

Representative first-wave output examples:
- `atm_iv_30d`
- `atm_iv_60d`
- `iv_term_slope_30d_60d`
- `put_call_skew_30d`
- `put_call_oi_ratio`
- `put_call_volume_ratio`
- `front_expiry_oi_share`
- `avg_option_spread_pct`
- `atm_option_spread_pct`
- `option_liquidity_score`

## Boundary rule

The data layer should preserve as much stable options information as practical.

The model layer decides:
- which full-chain information is used for option-specific decisioning
- which compressed context features are exposed to state/strategy models
- which features are ignored in a given model generation

Do not force the data layer to pre-delete derivatives information merely because some model families may not consume it immediately.
