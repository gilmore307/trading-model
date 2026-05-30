import unittest

from model_governance.evaluation.layer_metric_contracts import (
    METRIC_FAMILY_DESCRIPTIONS,
    all_layer_metric_contracts,
    layer_metric_contract,
    layer_metric_contract_payload,
)


class LayerMetricContractTests(unittest.TestCase):
    def test_contract_covers_all_ten_layers(self) -> None:
        contracts = all_layer_metric_contracts()

        self.assertEqual([contract.layer for contract in contracts], list(range(1, 11)))
        self.assertEqual(len({contract.model_id for contract in contracts}), 10)
        for contract in contracts:
            self.assertTrue(contract.tests_for_role("primary"), contract.model_id)
            self.assertTrue(contract.tests_for_role("guardrail"), contract.model_id)
            self.assertTrue(contract.tests_for_role("avoid"), contract.model_id)

    def test_binary_metrics_are_eligible_only_when_label_is_explicit(self) -> None:
        layer_five = layer_metric_contract(5)
        binary_tests = [test for test in layer_five.tests if "AUROC" in test.label or "Brier" in test.label]

        self.assertTrue(binary_tests)
        for test in binary_tests:
            self.assertIn("explicit", test.eligibility.lower())
            self.assertIn("probability", test.eligibility.lower())

    def test_option_expression_contract_does_not_use_underlying_only_pnl(self) -> None:
        layer_nine = layer_metric_contract(9)

        self.assertIn("option_expression", layer_nine.metric_families)
        avoided = {test.metric_id for test in layer_nine.tests_for_role("avoid")}
        self.assertIn("underlying_only_pnl_as_option_score", avoided)

    def test_payload_exposes_group_supplemental_tests(self) -> None:
        payload = layer_metric_contract_payload()

        self.assertIn("group_contribution", METRIC_FAMILY_DESCRIPTIONS)
        self.assertEqual(len(payload["layers"]), 10)
        self.assertTrue(payload["model_group_supplemental_tests"])


if __name__ == "__main__":
    unittest.main()
