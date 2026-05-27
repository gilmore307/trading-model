# M02 - Sector Context / SectorContextModel

This file records the active direction-neutral `trading-model` contract and implementation target for Layer 2. The current physical implementation still uses `sector_context_state` / `model_02_sector_context`; the accepted conceptual boundary is ETF-context state construction plus target-context routing.

## Input

```text
trading_model.model_01_market_regime   # Layer 1 primary output, consumed conceptually as market_context_state
trading_data.feature_02_sector_context
```

Layer 2 needs the Layer 1 output in addition to the Layer 2 data feature surface. `model_01_market_regime` / `market_context_state` is conditioning context only; it should shape interpretation of sector behavior but should not become sector, ETF, stock, or strategy selection by itself.

Layer 2 consumes sector/industry/theme ETF behavior evidence from `feature_02_sector_context`. The data-owned source rows behind that feature surface are provenance/construction evidence, not a separate direct model dependency unless a later accepted contract creates one. ETF holdings and `stock_etf_exposure` are not Layer 2 core behavior inputs; they belong downstream to anonymous target candidate construction unless a later accepted dynamic influence profile supersedes the static holdings route.

## Stage flow

```mermaid
flowchart LR
    l1["trading_model.model_01_market_regime<br/>Layer 1 market_context_state"]
    feature["trading_data.feature_02_sector_context<br/>sector/industry behavior feature surface"]
    model["SectorContextModel<br/>Layer 2 model logic"]
    output["trading_model.model_02_sector_context<br/>primary context_etf_state / current sector_context_state surface"]
    explain["trading_model.model_02_sector_context_explainability<br/>human-review behavior and attribution"]
    diagnostics["trading_model.model_02_sector_context_diagnostics<br/>acceptance and gating evidence"]
    builder["anonymous target candidate builder<br/>uses selected sector context plus holdings/exposure evidence"]

    l1 --> model
    feature --> model
    model --> output --> builder
    model --> explain
    model --> diagnostics
```

## Physical artifacts

```text
trading_model.model_02_sector_context
trading_model.model_02_sector_context_explainability
trading_model.model_02_sector_context_diagnostics
```

## `model_02_sector_context` - context ETF state output

The primary Layer 2 per-ETF output is one `context_etf_state` per eligible Layer 2 ETF at `available_time`. The current physical table and field names still use the earlier `sector_context_state` vocabulary, but downstream design should treat the row as an ETF-context state, not as a stock-sector membership row.

The primary output is the narrow, stable downstream contract. It contains identity, direction-neutral trend/tradability state, downstream ETF-context handoff, and eligibility/quality summary fields:

```text
available_time
sector_or_industry_symbol
model_id
model_version
market_context_state_ref
2_sector_relative_direction_score
2_sector_trend_quality_score
2_sector_trend_stability_score
2_sector_transition_risk_score
2_market_context_support_score
2_sector_breadth_confirmation_score
2_sector_internal_dispersion_score
2_sector_crowding_risk_score
2_sector_liquidity_tradability_score
2_sector_tradability_score
2_sector_handoff_state
2_sector_handoff_bias
2_sector_handoff_rank
2_sector_handoff_reason_codes
2_eligibility_state
2_eligibility_reason_codes
2_state_quality_score
2_coverage_score
2_data_quality_score
2_evidence_count
```

`sector_or_industry_symbol` currently names the context ETF/basket row. It should migrate conceptually to `context_etf_symbol` in new contracts. It is audit/routing identity for the ETF-context state and must not be copied as raw ticker identity into anonymous target fitting vectors.

`2_sector_relative_direction_score` is signed current sector-context direction evidence. Positive values indicate relative long bias and negative values indicate relative short bias; the sign is not a quality judgment and must not be interpreted as portfolio weight.

`2_market_context_support_score` is direction-aware support for the current sector state, not a bullish-market proxy. A weak market can support a weak/short-bias sector state.

`2_sector_internal_dispersion_score` and `2_sector_crowding_risk_score` are separate because dispersion/fragmentation and one-factor crowding are different risks.

`2_sector_tradability_score` is direction-neutral. It represents how clean, stable, liquid, low-noise, and low-transition-risk the sector context is for downstream anonymous target construction.

`2_state_quality_score`, `2_coverage_score`, and `2_data_quality_score` describe reliability/completeness of the produced state row. They are not opportunity scores and must not be blended silently with tradability or direction.

Allowed `2_sector_handoff_state` values are:

```text
selected | watch | blocked | insufficient_data
```

Allowed `2_sector_handoff_bias` values are:

```text
long_bias | short_bias | neutral | mixed
```

`2_sector_handoff_state` and `2_sector_handoff_bias` must stay separate. A stable weak sector can be `selected` with `short_bias`; a fast rising but noisy sector can be `watch` or `blocked` with `long_bias`.

Handoff, eligibility, rank, and reason-code fields are routing/audit outputs, not ordinary raw evidence fields. Research/evaluation should preserve selected, watch, blocked, and neutral/blocked control samples so downstream training does not learn only from preselected states.

## Target-context routing

Layer 2 has three target routing cases:

| Target class | Examples | Layer 2 handling |
|---|---|---|
| Layer 1 market ETF target | `SPY`, `QQQ`, `IWM`, `DIA`, broad Layer 1 market rows | Do not map to a sector ETF. Use Layer 1 `market_context_state` directly, and use Layer 2 `cross_etf_summary` only as supporting market-breadth/rotation context. |
| Layer 2 context ETF target | `XLE`, `XLK`, `SMH`, `XBI`, reviewed Layer 2 context ETFs | Use the target ETF's own `context_etf_state` directly with self-context influence `1.0`, plus `cross_etf_summary` for its relative position. Layer 3 still owns the ETF target's own target-local price/tape state. |
| Ordinary target | Common stocks and other non-context targets | Build or consume a `target_context_profile` that maps the target to one or more `context_etf_state` rows with dynamic influence weights, correlation, lead-lag direction, and confidence. Holdings/manual mappings are seed or fallback evidence, not the final scientific standard. |

This routing keeps Layer 2 from forcing every target into a static sector label. Layer 2 produces ETF context states and routing/influence evidence; Layer 3+ decides how a selected target consumes those contexts.

## Cross-ETF summary boundary

Layer 2 may emit a global or group-level `cross_etf_summary` that ranks and summarizes context ETFs for rotation/attention. It answers which ETF contexts are relatively strong, weak, crowded, dispersive, or clean.

Per-ETF cross-section calculations are internal construction evidence for `context_etf_state`. A `context_etf_cross_section_row` must not become a separate downstream output when the same information is already embedded in `context_etf_state`; otherwise consumers would have two competing sources for one state.

## `model_02_sector_context_explainability` - explainability

Explainability owns human-review detail that should not become a hard downstream dependency:

- observed behavior internals such as relative strength, trend direction, volatility-adjusted trend, breadth, dispersion, correlation, and chop;
- inferred attribute internals such as growth/defensive/cyclical/rate/dollar/commodity/risk-appetite sensitivity and attribute certainty;
- conditional behavior internals such as beta, directional coupling, volatility response, capture asymmetry, response convexity, context support, and transition sensitivity;
- contributing evidence and reason-code detail.

## `model_02_sector_context_diagnostics` - diagnostics

Diagnostics owns acceptance, monitoring, and gating evidence:

- liquidity/spread/optionability/capacity/tradability;
- event/gap/volatility/correlation stress and downside-tail risk;
- coverage/freshness/missingness;
- baseline comparison;
- refit stability;
- no-future-leak checks.

## Naming rule

Layer 2 model fields use compact `2_*` names in docs, model-facing payloads, and SQL physical columns. SQL writers should quote numeric-leading column names when needed rather than storing semantic aliases such as `layer02_*`.

## Layer acceptance

Layer 2 changes are acceptable when they:

- consume `trading_model.model_01_market_regime` / `market_context_state` as conditioning context plus `trading_data.feature_02_sector_context` as the deterministic feature surface;
- keep Layer 1 context from becoming sector, ETF, stock, strategy, option, or portfolio selection by itself;
- exclude ETF holdings and `stock_etf_exposure` from core Layer 2 behavior modeling unless a later accepted contract moves that boundary;
- preserve `model_02_sector_context` as the current narrow downstream ETF-context output surface and keep explainability/diagnostics as support surfaces;
- implement target routing with the three accepted cases: Layer 1 ETF target, Layer 2 context ETF target, and ordinary target with dynamic context-profile weighting;
- avoid promoting `context_etf_cross_section_row` as a separate output when it is only construction evidence for `context_etf_state`;
- keep sector direction, trend quality, transition risk, tradability, state quality, and handoff bias as separate semantics rather than collapsing them into a single readiness score;
- route new shared names, statuses, fields, handoff states, or reason-code vocabularies through `trading-manager/scripts/` before cross-repository dependence.

## Production promotion

`model_02_sector_context` must not become a production-hard downstream dependency until it has a reviewed promotion candidate backed by real-data evaluation evidence. Promotion evidence must include explicit thresholds, metric values, baseline comparison, split/refit stability, sector handoff quality, and no-future-leak checks. Fixture/local dry-run evidence should defer.

Current real-data status: V2.2 `model_02_sector_context` rows and real promotion evidence exist, but the latest read-only evidence remains **deferred**, not approved. Missing model rows at label decision times are tracked as alignment/completeness evidence, not future leakage; leakage means label-time or split-order violations. No-future-leak and chronological split-overlap checks pass, while current promotion remains blocked by model/label alignment, coverage/pair-count, baseline, stability, and sector handoff gates. Fixture/local dry-run evidence must defer.

Current Layer 2 verification covers the V2.2 deterministic generator, SQL physical-artifact writers, direction-neutral promotion evidence builders, and contract boundary checks:

```bash
git diff --check
python3 -m compileall -q src scripts tests
PYTHONPATH=src python3 -m unittest tests.test_sector_context_contract tests.test_sector_context_model tests.test_sector_context_evaluation
rg -n "source_02_sector_context|layer02_|SecuritySelectionModel|security_selection" docs src scripts tests
```
