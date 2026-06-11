"""Build Layer 4 input rows from accepted M06 focus-pool replay evidence."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def build_layer4_focus_pool_input_rows(
    *,
    replay_overlay_rows: Iterable[Mapping[str, Any]],
    gate_matrix_rows: Iterable[Mapping[str, Any]],
    model_version: str = "m06_residual_event_governance_focus_pool_contract",
) -> list[dict[str, Any]]:
    accepted = {
        str(row.get("family_key") or "")
        for row in gate_matrix_rows
        if str(row.get("focus_pool_status") or "") == "accepted_temporal_attention_focus_pool"
        and str(row.get("production_route_decision") or "").startswith("approve_focus_pool_entry")
    }
    output: list[dict[str, Any]] = []
    for row in replay_overlay_rows:
        families = _as_list(row.get("visible_event_families"))
        event_ids = _as_list(row.get("visible_event_ids"))
        window_policies = _as_list(row.get("visible_event_window_policies"))
        accepted_items = [
            (family, _at(event_ids, index), _at(window_policies, index))
            for index, family in enumerate(families)
            if family in accepted
        ]
        accepted_families = [family for family, _, _ in accepted_items]
        if not accepted_families:
            continue
        decision_id = str(row.get("decision_id") or "").strip()
        available_time = row.get("replay_time_pointer") or row.get("available_time")
        if not decision_id or not available_time:
            continue
        suffix = "1D"
        output.append(
            {
                "available_time": available_time,
                "tradeable_time": available_time,
                "target_candidate_id": f"m06_residual_event_governance_replay_{decision_id}",
                "m06_residual_event_governance_contract_ref": row.get("event_context_vector_ref"),
                "m06_residual_event_governance_contract": {
                    "contract_owner": "model_06_residual_event_governance",
                    "model_version": model_version,
                    "production_route_decision": "approve_focus_pool_entry",
                    "focus_pool_status": "accepted_temporal_attention_focus_pool",
                    "accepted_event_families": accepted_families,
                    "visible_event_ids": [event_id for _, event_id, _ in accepted_items if event_id],
                    "visible_event_window_policies": [policy for _, _, policy in accepted_items if policy],
                    "6_event_presence_score_1D": row.get(f"6_event_presence_score_{suffix}"),
                    "6_event_timing_proximity_score_1D": row.get(f"6_event_timing_proximity_score_{suffix}"),
                    "6_event_intensity_score_1D": row.get(f"6_event_intensity_score_{suffix}"),
                    "6_event_gap_risk_score_1D": row.get(f"6_event_gap_risk_score_{suffix}"),
                    "6_event_reversal_risk_score_1D": row.get(f"6_event_reversal_risk_score_{suffix}"),
                    "6_event_underlying_impact_score_1D": row.get(f"6_event_underlying_impact_score_{suffix}"),
                    "6_event_option_impact_score_1D": row.get(f"6_event_option_impact_score_{suffix}"),
                },
            }
        )
    return output


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                if isinstance(payload, Mapping):
                    rows.append(dict(payload))
    return rows


def read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def _as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, tuple):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return [part for part in stripped.split(";") if part]
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item)]
        return [str(parsed)]
    return []


def _at(values: Sequence[str], index: int) -> str:
    return values[index] if index < len(values) else ""


__all__ = [
    "build_layer4_focus_pool_input_rows",
    "read_csv",
    "read_jsonl",
    "write_jsonl",
]
