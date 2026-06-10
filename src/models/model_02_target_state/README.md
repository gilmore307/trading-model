# model_02_target_state

Canonical package boundary for current `M02 Target State`.

This model owns target eligibility, target ranking, anonymous target-state evidence, and target selection context. It preserves the identity boundary: raw ticker/company identity is audit/routing metadata, not a fitting feature.

The current deterministic pilot consumes `background_context_state` and anonymous target features, then emits `target_context_state`, `target_context_state_ref`, and `2_*` target scores. Model-facing payloads are sanitized so raw ticker/company identifiers do not enter `target_context_state`.

Retired `model_03_target_state_vector` remains a migration-source surface only.
