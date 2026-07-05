from __future__ import annotations

import unittest

from models import state_vector_feature_registry as registry
from models.model_01_background_context import contract as model_01_contract
from models.model_02_target_state import contract as model_02_contract
from models.model_03_event_state import contract as model_03_contract
from models.model_04_unified_decision import contract as model_04_contract
from models.model_05_option_expression import contract as model_05_option_contract


class StateVectorFeatureRegistryTests(unittest.TestCase):
    def test_feature_semantics_are_explicit_and_valid(self) -> None:
        registry.validate_feature_semantics()
        by_field = registry.semantics_by_field()

        self.assertEqual(by_field["1_market_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["1_market_risk_stress_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["2_target_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["2_tradability_score_<horizon>"].feature_use, "model_facing")
        self.assertEqual(by_field["3_event_path_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["4_edge_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["4_direction_thesis_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["4_direction_certainty_score_<horizon>"].score_class, "direction_strength")
        self.assertEqual(by_field["4_downside_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["3_event_symbol_impact_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["3_event_scope_escalation_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["5_option_expression_direction_score_<horizon>"].high_value_meaning, "signed")
        self.assertEqual(by_field["5_option_theta_risk_score_<horizon>"].high_value_meaning, "bad")
        self.assertEqual(by_field["5_option_liquidity_fit_score_<horizon>"].score_class, "liquidity")
        self.assertEqual(by_field["5_option_expression_confidence_score_<horizon>"].feature_use, "model_facing")

    def test_old_layer_surfaces_are_not_registered(self) -> None:
        by_field = registry.semantics_by_field()

        self.assertNotIn("5_alpha_direction_score_<horizon>", by_field)
        self.assertNotIn("7_target_exposure_score_<horizon>", by_field)
        self.assertNotIn("8_underlying_action_direction_score_<horizon>", by_field)

    def test_current_contract_score_families_are_registered(self) -> None:
        by_field = registry.semantics_by_field()
        required_fields = (
            model_01_contract.SCORE_FAMILIES
            + model_02_contract.SCORE_FAMILIES
            + model_03_contract.SCORE_FAMILIES
            + model_04_contract.SCORE_FAMILIES
            + model_05_option_contract.SCORE_FAMILIES
        )

        missing = [field for field in required_fields if field not in by_field]
        self.assertEqual([], missing)


if __name__ == "__main__":
    unittest.main()
