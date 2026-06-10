import unittest

from models.model_sequence import model_sequence_rows


class ModelSequenceTests(unittest.TestCase):
    def test_model_stack_has_six_m_prefixed_display_sequence(self) -> None:
        rows = model_sequence_rows()

        self.assertEqual([row["model_step"] for row in rows], [f"M{index:02d}" for index in range(1, 7)])
        self.assertEqual(rows[0]["model_name"], "Background Context")
        self.assertEqual(rows[0]["model_surface"], "model_01_background_context")
        self.assertEqual(rows[-1]["model_name"], "Residual Event Governance")
        self.assertEqual(rows[-1]["model_surface"], "model_06_residual_event_governance")
        self.assertTrue(all(row["contract_type"] == "trading_model_sequence" for row in rows))

    def test_m_sequence_preserves_six_stable_model_surfaces(self) -> None:
        rows = model_sequence_rows()

        self.assertEqual(
            [row["model_surface"] for row in rows],
            [
                "model_01_background_context",
                "model_02_target_state",
                "model_03_event_state",
                "model_04_unified_decision",
                "model_05_option_expression",
                "model_06_residual_event_governance",
            ],
        )


if __name__ == "__main__":
    unittest.main()
