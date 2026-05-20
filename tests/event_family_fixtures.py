from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from models.model_10_event_risk_governor.event_family_all_association import (
    build_event_family_all_association,
    write_event_family_all_association_artifacts,
)
from models.model_10_event_risk_governor.event_family_batch_catalog import (
    build_event_family_batch_catalog,
    write_catalog_artifacts,
)
from models.model_10_event_risk_governor.event_family_empirical_coverage import (
    EXISTING_EMPIRICAL_ARTIFACTS,
    build_event_family_empirical_coverage,
    write_empirical_coverage_artifacts,
)
from models.model_10_event_risk_governor.event_family_precondition_completion import (
    build_event_family_precondition_completion,
    write_precondition_artifacts,
)
from models.model_10_event_risk_governor.event_family_remaining_acceptance import (
    build_event_family_remaining_acceptance,
    write_acceptance_artifacts,
)


@dataclass(frozen=True)
class EventFamilyFixture:
    root: Path
    model_root: Path
    trading_data_root: Path
    catalog_path: Path
    remaining_acceptance_path: Path
    precondition_path: Path
    coverage_path: Path
    association_dir: Path
    runtime_root: Path
    source_root: Path
    bar_root: Path


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _write_text_artifacts(model_root: Path) -> None:
    for refs in EXISTING_EMPIRICAL_ARTIFACTS.values():
        for ref in refs:
            path = Path(ref)
            if path.is_absolute():
                continue
            _write_json(model_root / path, {"fixture": True})


def _write_trading_data_fixture(trading_data_root: Path) -> None:
    macro_rows = [
        {
            "event_time": "2016-01-08T08:30:00-05:00",
            "event": "Non Farm Payrolls",
            "source_event_type": "macro_calendar",
            "actual": "200K",
            "consensus": "190K",
            "te_forecast": "191K",
            "reference": "2015-12",
        },
        {
            "event_time": "2016-01-15T08:30:00-05:00",
            "event": "CPI Inflation Rate YoY",
            "source_event_type": "macro_calendar",
            "actual": "0.3",
            "consensus": "0.1",
            "te_forecast": "0.2",
            "reference": "2015-12",
        },
    ]
    macro_fields = ["event_time", "event", "source_event_type", "actual", "consensus", "te_forecast", "reference"]
    _write_csv(
        trading_data_root
        / "storage"
        / "monthly_backfill"
        / "trading_economics_calendar_web"
        / "2016-01"
        / "runs"
        / "fixture_run"
        / "saved"
        / "trading_economics_calendar_event.csv",
        macro_fields,
        macro_rows,
    )
    _write_json(
        trading_data_root / "storage/monthly_backfill/trading_economics_calendar_web/2016-01/completion_receipt.json",
        {"runs": [{"row_counts": {"trading_economics_calendar_event": len(macro_rows)}}]},
    )

    news_rows = [
        {
            "created_at": "2016-01-11T09:30:00-05:00",
            "timeline_headline": "Acme announces merger agreement",
            "summary": "Merger deal candidate fixture.",
        },
        {
            "created_at": "2016-01-12T09:30:00-05:00",
            "timeline_headline": "Acme product launch update",
            "summary": "Product launch fixture.",
        },
        {
            "created_at": "2016-01-13T09:30:00-05:00",
            "timeline_headline": "Sector demand and inventory report",
            "summary": "Demand sales orders inventory fixture.",
        },
    ]
    _write_csv(
        trading_data_root / "storage/monthly_backfill/alpaca_news/2016-01/runs/fixture_run/saved/equity_news.csv",
        ["created_at", "timeline_headline", "summary"],
        news_rows,
    )

    bar_rows: list[dict[str, object]] = []
    for day in range(4, 29):
        close = 100.0 if day < 15 else 100.2
        bar_rows.append(
            {
                "timestamp": f"2016-01-{day:02d}T16:00:00-05:00",
                "bar_open": close,
                "bar_high": close + 0.1,
                "bar_low": close - 0.1,
                "bar_close": close,
            }
        )
    for symbol in ["TLT", "SPY"]:
        _write_csv(
            trading_data_root / f"storage/monthly_backfill/alpaca_bars/{symbol}/2016-01/runs/fixture_run/saved/equity_bar.csv",
            ["timestamp", "bar_open", "bar_high", "bar_low", "bar_close"],
            bar_rows,
        )
        _write_json(
            trading_data_root / f"storage/monthly_backfill/alpaca_bars/{symbol}/2016-01/completion_receipt.json",
            {"runs": [{"row_counts": {"equity_bar": len(bar_rows)}}]},
        )


def _write_runtime_fixture(runtime_root: Path) -> None:
    labels = []
    for idx in range(12):
        labels.append(
            {
                "target_candidate_id": f"fixture_{idx}",
                "available_time": "2016-01-15T10:00:00-05:00",
                "underlying_action_plan_ref": f"plan_{idx}",
                "planned_underlying_action_type": "no_trade",
                "planned_action_side": "none",
                "realized_underlying_return_after_entry": 0.035,
                "realized_net_underlying_utility": 0.0,
                "no_trade_opportunity_cost": 0.035,
                "no_trade_missed_positive_utility_rate": 1.0,
                "no_trade_avoided_negative_utility_rate": 0.0,
            }
        )
    _write_json(
        runtime_root / "model_08_underlying_action/evaluation_summary_2016-01.json",
        {"labels": labels},
    )
    _write_jsonl(
        runtime_root / "model_08_underlying_action/model_rows_2016-01.jsonl",
        [
            {
                "underlying_action_plan_ref": f"plan_{idx}",
                "underlying_action_plan": {"reason_codes": ["fixture_base_stack_reason"]},
            }
            for idx in range(12)
        ],
    )


def _patch_threshold_fixture(path: Path) -> None:
    rows: list[dict[str, str]] = []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        for row in reader:
            if row.get("family_key") == "equity_offering_dilution":
                row["association_class"] = "local_screening_risk_association_unaccepted"
                row["screening_stability_status"] = "expanded_screening_threshold_review_candidate"
                row["event_count"] = "5"
                row["max_label_count"] = "50"
                row["risk_material_metric_count"] = "2"
            rows.append(row)
    _write_csv(path, fieldnames, rows)


def build_event_family_fixture(root: Path) -> EventFamilyFixture:
    root.mkdir(parents=True, exist_ok=True)
    model_root = root / "model"
    trading_data_root = root / "trading-data"
    runtime_root = root / "runtime"
    _write_text_artifacts(model_root)
    _write_trading_data_fixture(trading_data_root)
    _write_runtime_fixture(runtime_root)

    catalog_dir = root / "event_family_batch_catalog_20260516"
    catalog = build_event_family_batch_catalog(root=model_root, generated_at_utc="2026-05-16T10:00:00+00:00")
    write_catalog_artifacts(catalog, catalog_dir)
    catalog_path = catalog_dir / "event_family_batch_catalog.json"

    remaining_dir = root / "event_family_remaining_acceptance_20260516"
    remaining = build_event_family_remaining_acceptance(
        catalog_path=catalog_path,
        generated_at_utc="2026-05-16T16:00:00+00:00",
    )
    write_acceptance_artifacts(remaining, remaining_dir)
    remaining_path = remaining_dir / "event_family_remaining_acceptance.json"

    precondition_dir = root / "event_family_precondition_completion_20260516"
    precondition = build_event_family_precondition_completion(
        catalog_path=catalog_path,
        acceptance_path=remaining_path,
        generated_at_utc="2026-05-16T22:00:00+00:00",
    )
    write_precondition_artifacts(precondition, precondition_dir)
    precondition_path = precondition_dir / "event_family_precondition_completion.json"

    coverage_dir = root / "event_family_empirical_coverage_20260516"
    coverage = build_event_family_empirical_coverage(
        precondition_path=precondition_path,
        trading_data_root=trading_data_root,
        model_root=model_root,
        generated_at_utc="2026-05-17T02:00:00+00:00",
    )
    write_empirical_coverage_artifacts(coverage, coverage_dir)
    coverage_path = coverage_dir / "event_family_empirical_coverage.json"

    association_dir = root / "event_family_all_association_20260516"
    source_root = trading_data_root / "storage/monthly_backfill"
    bar_root = source_root / "alpaca_bars"
    association = build_event_family_all_association(
        coverage_path=coverage_path,
        source_root=source_root,
        bar_root=bar_root,
        generated_at_utc="2026-05-17T03:00:00+00:00",
    )
    write_event_family_all_association_artifacts(association, association_dir)
    _patch_threshold_fixture(association_dir / "event_family_expanded_stability.csv")

    return EventFamilyFixture(
        root=root,
        model_root=model_root,
        trading_data_root=trading_data_root,
        catalog_path=catalog_path,
        remaining_acceptance_path=remaining_path,
        precondition_path=precondition_path,
        coverage_path=coverage_path,
        association_dir=association_dir,
        runtime_root=runtime_root,
        source_root=source_root,
        bar_root=bar_root,
    )
