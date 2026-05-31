import unittest

from models.model_sequence import model_sequence_rows


class ModelSequenceTests(unittest.TestCase):
    def test_model_stack_has_m_prefixed_display_sequence(self) -> None:
        rows = model_sequence_rows()

        self.assertEqual([row["model_step"] for row in rows], [f"M{index:02d}" for index in range(1, 11)])
        self.assertEqual(rows[0]["model_name"], "Market Regime")
        self.assertEqual(rows[0]["model_surface"], "m01_market_regime_model_generation")
        self.assertEqual(rows[-1]["model_name"], "Event Risk Governor")
        self.assertEqual(rows[-1]["model_surface"], "model_10_event_risk_governor")
        self.assertTrue(all(row["contract_type"] == "trading_model_sequence" for row in rows))

    def test_m_sequence_preserves_stable_model_surfaces(self) -> None:
        rows = model_sequence_rows()

        self.assertEqual(
            [row["model_surface"] for row in rows],
            [
                "m01_market_regime_model_generation",
                "m02_sector_context_model_generation",
                "model_03_target_state_vector",
                "model_04_event_failure_risk",
                "model_05_alpha_confidence",
                "model_06_dynamic_risk_policy",
                "model_07_position_projection",
                "model_08_underlying_action",
                "model_09_option_expression",
                "model_10_event_risk_governor",
            ],
        )


if __name__ == "__main__":
    unittest.main()
