# model_09_option_expression

Physical package for the Layer 9 `OptionExpressionModel` / trading-guidance option-expression scaffold.

Owns local conversion from Layer 8 `underlying_action_plan` / option-expression handoff fields plus point-in-time option-chain candidates into `option_expression_plan` and `expression_vector` rows when an option chain is available. The scaffold implements:

- long-call / long-put / no-option expression resolution from the Layer 8 underlying path thesis;
- point-in-time contract candidate scoring across DTE, delta/Greeks, IV, spread/liquidity, fill quality, and reward/risk;
- selected contract references and option-expression constraints without order routing;
- explicit offline option-surface status evidence for optionable, missing-chain, and non-optionable direct-underlying routes;
- offline option-expression labels and leakage assertions in `evaluation.py`.

Offline training and evaluation may retain dense underlying-minute option-surface status evidence wherever Layer 8 thesis context exists. Only optionable rows with point-in-time option-chain snapshots create M09 contract/expression candidate rows. Optionable rows without a snapshot and non-optionable routes such as BTC are bypass/status evidence for coverage and audit; live C04 should bypass M09 for those cases and must not ask M09 to score missing contracts. Selected-contract thresholds and expression hard filters are outputs or routing policies, not training-row admission filters.

Boundary: this package may select option-expression and contract constraints, but must not emit order type, route, final order quantity, broker order id, execution instruction, or broker/account mutation fields.
