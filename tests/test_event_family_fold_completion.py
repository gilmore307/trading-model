from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from models.model_03_event_state.event_governance.fold_completion import (
    build_event_family_fold_completion,
    write_event_family_fold_completion_artifacts,
)


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class EventFamilyFoldCompletionTests(unittest.TestCase):
    def test_completion_keeps_calibrated_and_keyword_families_separate(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            catalog = _write(
                tmp / "catalog.json",
                {
                    "candidates": [
                        {
                            "family_key": "cpi_inflation_release",
                            "accepted_current_use": "macro_risk_control",
                            "blocked_use": "standalone_alpha",
                            "blocker_codes": ["canonical_history_needed"],
                            "evidence_refs": ["cpi_evidence"],
                        },
                        {
                            "family_key": "equity_offering_dilution",
                            "accepted_current_use": "candidate_only",
                            "blocked_use": "directional_alpha",
                            "blocker_codes": ["missing_family_packet"],
                            "evidence_refs": [],
                        },
                    ]
                },
            )
            acceptance = _write(
                tmp / "acceptance.json",
                {
                    "family_rows": [
                        {
                            "family_key": "cpi_inflation_release",
                            "acceptance_status": "risk_only_candidate_pending_canonical_evidence",
                            "accepted_current_use": "macro_risk_surprise_control_pending_canonical_te_history",
                            "blocked_use": "standalone_alpha",
                            "blocker_codes": ["canonical_te_expectation_history_needed"],
                            "evidence_refs": ["cpi_acceptance"],
                            "next_action": "expand canonical history",
                        },
                        {
                            "family_key": "equity_offering_dilution",
                            "acceptance_status": "packet_required_high_priority",
                            "accepted_current_use": "candidate_only",
                            "blocked_use": "directional_alpha",
                            "blocker_codes": ["missing_family_packet"],
                            "evidence_refs": [],
                            "next_action": "build packet",
                        },
                    ]
                },
            )
            coverage = _write(
                tmp / "coverage.json",
                {
                    "family_rows": [
                        {
                            "family_key": "cpi_inflation_release",
                            "association_readiness_status": "partial_ready_risk_only_after_fuller_te_history",
                        },
                        {
                            "family_key": "equity_offering_dilution",
                            "association_readiness_status": "not_ready_expand_source_or_parser_first",
                        },
                    ]
                },
            )
            precondition = _write(
                tmp / "precondition.json",
                {
                    "packets": [
                        {
                            "family_key": "cpi_inflation_release",
                            "packet_status": "packet_spec_completed_current_risk_only_evidence",
                            "remaining_blocker_codes": [],
                        },
                        {
                            "family_key": "equity_offering_dilution",
                            "packet_status": "packet_spec_completed_pending_empirical_evidence",
                            "remaining_blocker_codes": ["empirical_association_study_required"],
                        },
                    ]
                },
            )
            association = _write(
                tmp / "association.json",
                {
                    "family_rows": [
                        {
                            "family_key": "cpi_inflation_release",
                            "association_class": "risk_volatility_association_not_directional_alpha",
                            "risk_control_supported": True,
                        },
                        {
                            "family_key": "equity_offering_dilution",
                            "association_class": "not_measured_data_gap",
                            "risk_control_supported": False,
                        },
                    ]
                },
            )
            impact = _write(
                tmp / "impact.json",
                {
                    "selected_windows": {
                        "cpi_inflation_release": {"selected_window_label": "minus_3_to_event"},
                        "triple_witching_calendar": {"selected_window_label": "minus_3_to_event"},
                    }
                },
            )
            replay = _write(
                tmp / "replay.json",
                {
                    "event_input_family_keys": [
                        "cpi_inflation_release",
                        "equity_offering_dilution",
                        "triple_witching_calendar",
                    ],
                    "matched_event_counts_by_family": {
                        "cpi_inflation_release": 5,
                        "equity_offering_dilution": 3,
                        "triple_witching_calendar": 2,
                    },
                },
            )

            completion = build_event_family_fold_completion(
                catalog_path=catalog,
                acceptance_path=acceptance,
                precondition_path=precondition,
                coverage_path=coverage,
                association_path=association,
                impact_window_summary_path=impact,
                replay_summary_path=replay,
                fold_id="fold",
                replay_run_id="run",
            )

        by_family = {row.family_key: row for row in completion.family_rows}
        self.assertEqual(by_family["cpi_inflation_release"].impact_window_status, "calibrated_impact_window_applied")
        self.assertEqual(
            by_family["cpi_inflation_release"].fold1_completion_status,
            "fold1_complete_production_route_reviewed",
        )
        self.assertEqual(by_family["cpi_inflation_release"].production_route_review_status, "agent_review_complete")
        self.assertEqual(
            by_family["cpi_inflation_release"].production_route_decision,
            "approve_focus_pool_entry_risk_control_only",
        )
        self.assertEqual(
            by_family["cpi_inflation_release"].focus_pool_status,
            "accepted_temporal_attention_focus_pool",
        )
        self.assertEqual(
            by_family["equity_offering_dilution"].impact_window_status,
            "same_day_keyword_observation_unvalidated",
        )
        self.assertEqual(
            by_family["equity_offering_dilution"].production_completion_status,
            "production_route_review_blocked_unvalidated_impact_window",
        )
        self.assertEqual(
            by_family["equity_offering_dilution"].focus_pool_status,
            "deferred_from_temporal_attention_focus_pool",
        )
        self.assertEqual(by_family["triple_witching_calendar"].packet_status, "complete")
        self.assertTrue(completion.summary["fold1_evidence_complete"])
        self.assertFalse(completion.summary["event_family_effect_model_evidence_complete"])

    def test_writer_emits_summary_and_gate_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as raw_tmp:
            tmp = Path(raw_tmp)
            path = _write(tmp / "empty.json", {"candidates": []})
            list_path = _write(tmp / "empty_rows.json", {"family_rows": []})
            impact = _write(tmp / "impact.json", {"selected_windows": {}})
            replay = _write(tmp / "replay.json", {"event_input_family_keys": [], "matched_event_counts_by_family": {}})
            completion = build_event_family_fold_completion(
                catalog_path=path,
                acceptance_path=list_path,
                precondition_path=list_path,
                coverage_path=list_path,
                association_path=list_path,
                impact_window_summary_path=impact,
                replay_summary_path=replay,
                fold_id="fold",
                replay_run_id="run",
            )
            out = tmp / "out"
            write_event_family_fold_completion_artifacts(completion, out)

            self.assertTrue((out / "event_family_fold_completion.json").exists())
            self.assertTrue((out / "event_family_fold_completion_summary.json").exists())
            self.assertTrue((out / "event_family_gate_matrix.csv").exists())


if __name__ == "__main__":
    unittest.main()
