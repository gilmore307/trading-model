# anonymous_target_candidate_builder

Layer 3 candidate-preparation sub-boundary for building anonymous target candidates from Layer 2 sector context.

Current status: contract plus first deterministic implementation complete; production use still depends on reviewed real-data Layer 3 evidence.

Boundary:

- Input: Layer 2 selected/watch `sector_context_state` rows with separate handoff bias, point-in-time ETF holdings / `stock_etf_exposure` evidence, target-local behavior/liquidity/event/cost evidence, anonymous structural buckets, and references to `market_context_state`.
- Output: anonymous candidate rows keyed by `available_time + target_candidate_id` with a model-facing `anonymous_target_feature_vector`.
- Metadata: real symbol/company/routing references stay in audit/routing metadata, not model-facing fitting vectors; structural bucket combinations must be checked so they do not become identity surrogates.
- Downstream: `TargetStateVectorModel` and later target-aware layers consume anonymous features, not raw ticker identity.

Files:

- `target_candidate_builder_contract.md` — V1 row contract, anonymity boundary, allowed evidence, excluded fields, and evaluation requirements.
- `builder.py` — deterministic builder for anonymous candidate rows plus recursive model-facing identity/downstream-field leakage checks.
