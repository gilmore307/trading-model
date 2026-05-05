# trading-model

`trading-model` is the offline modeling repository for the seven-layer trading decision system.

It owns point-in-time model research, validation, decision-record prototypes, and model outputs for:

1. MarketRegimeModel (`market_regime_model`);
2. SectorContextModel (`sector_context_model`);
3. TargetStateVectorModel (`target_state_vector_model`);
4. TradeQualityModel (`trade_quality_model`);
5. OptionExpressionModel (`option_expression_model`);
6. EventOverlayModel (`event_overlay_model`);
7. PortfolioRiskModel (`portfolio_risk_model`).

It does not own raw source acquisition, live/paper order placement, broker/account mutation, global registry authority, generated runtime artifacts committed to Git, or secrets.

## Current Model Structure

The accepted structure separates market, sector, and target work:

```text
MarketRegimeModel
  -> market_context_state

SectorContextModel
  -> sector_context_state

anonymous target candidate builder + TargetStateVectorModel
  -> anonymous_target_feature_vector
  -> target_state_vector

TradeQualityModel -> OptionExpressionModel -> EventOverlayModel -> PortfolioRiskModel
```

Layer 1 describes broad market state only. Layer 2 describes sector/industry trend stability and inferred basket attributes under that market state. Layer 3+ evaluates anonymous target candidates; ticker/company identity stays in audit/routing metadata, not in model-facing fitting vectors.

## Top-Level Structure

```text
docs/        Repository scope/context, layer workflows with acceptance, task/decision/memory, and architecture references.
src/         Importable model-specific and shared-governance implementation code.
scripts/     SQL generation wrappers and operational entrypoints.
tests/       First-party unit tests using in-memory fixtures/fake cursors.
```

Current implementation packages:

```text
src/models/                           Model-specific packages and layer-boundary contracts.
src/models/model_01_market_regime/    MarketRegimeModel V2.2 generator, evaluation, config, and evidence map.
src/models/model_02_sector_context/ SectorContextModel V1 sector-context contract.
src/models/model_03_target_state_vector/ TargetStateVectorModel draft contract and Layer 3 state-vector workspace.
src/models/model_03_target_state_vector/anonymous_target_candidate_builder/ Candidate-preparation sub-boundary.
src/models/model_03_strategy_selection/ Legacy frozen strategy-selection research workspace.
src/model_governance/common/          Shared SQL, database-url, and `psql` helpers.
src/model_governance/evaluation/      Dataset/evaluation evidence schema helpers.
src/model_governance/promotion/       Promotion lifecycle rows, schema, persistence, activation, and agent review helpers.
```

Current runtime wrappers:

```text
scripts/models/model_01_market_regime/generate_model_01_market_regime.py
scripts/model_governance/ensure_model_governance_schema.py
scripts/models/model_01_market_regime/evaluate_model_01_market_regime.py
scripts/model_governance/clear_model_development_database.py
scripts/models/model_01_market_regime/run_market_regime_development_smoke.py
scripts/models/model_01_market_regime/review_market_regime_promotion.py
```

`evaluate_model_01_market_regime.py` is fixture/local-JSONL dry-run by default and has an explicit `--from-database` read-only path for real feature/model SQL rows. Its promotion summary includes metric values, explicit thresholds, baseline comparison, split-stability evidence, and no-future-leak checks.

`review_market_regime_promotion.py` is review-only by default. With `--write-decision`, it persists evaluation artifacts, config/candidate rows, and the reviewed promotion decision. With `--activate-approved-config`, accepted approval decisions insert a `model_promotion_activation` event and mark the reviewed config row active through `model_config_version`; deferred or rejected decisions leave the active config unchanged.

`src/` owns reusable model logic. `scripts/` may import `src/`; `src/` must not import `scripts/`.

## Docs Spine

```text
docs/
  00_scope.md
  01_context.md
  02_layer_01_market_regime.md
  03_layer_02_sector_context.md
  04_layer_03_target_state_vector.md
  80_task.md
  81_decision.md
  82_memory.md
  90_system_model_architecture_rfc.md
  91_model_decomposition.md
```

`docs/91_model_decomposition.md` is the model-design review template: each layer should be decomposed by data, features, target, model mapping, loss, training/update process, validation, overfitting control, and decision deployment before implementation or promotion expands. Layer-specific `02_`/`03_` docs now own workflow, artifact contracts, and acceptance gates for the active Layer 1 and Layer 2 boundaries.

## Platform Dependencies

- `trading-manager` owns global contracts, registry, shared helpers, templates, and platform guidance.
- `trading-data` owns raw acquisition and source-evidence bundles.
- `trading-storage` owns durable storage layout and retention unless this repository is proposing a reviewed storage contract.
- `trading-manager` owns control-plane orchestration and lifecycle routing.
- Execution-side repositories own broker/account mutation.

Any new global helper, reusable template, shared field, status, type, config key, or vocabulary discovered here must be routed back to `trading-manager` before other repositories depend on it.
