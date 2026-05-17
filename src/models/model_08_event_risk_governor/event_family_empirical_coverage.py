"""Scan local empirical coverage for all EventRiskGovernor event families.

This is a no-provider, no-training coverage/readiness pass. It looks only at
existing local artifacts and source backfill outputs to determine whether each
fine-grained family has candidate source evidence and what remains before a real
association study can be run.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence, TextIO
import glob
import re

CONTRACT_TYPE = "event_family_empirical_coverage_v1"
SUMMARY_CONTRACT_TYPE = "event_family_empirical_coverage_summary_v1"
DEFAULT_PRECONDITION_PATH = Path("storage/event_family_precondition_completion_20260516/event_family_precondition_completion.json")
DEFAULT_OUTPUT_DIR = Path("storage/event_family_empirical_coverage_20260516")
DEFAULT_TRADING_DATA_ROOT = Path("/root/projects/trading-data")

EXISTING_EMPIRICAL_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "earnings_guidance_scheduled_shell": ("storage/earnings_guidance_event_alone_q4_2025_20260515/report.json",),
    "earnings_guidance_result_metrics": (
        "storage/earnings_guidance_result_artifact_scout_q4_2025_20260515/report.json",
        "storage/earnings_guidance_expectation_baseline_readiness_q4_2025_20260515/report.json",
    ),
    "earnings_guidance_raise_cut_or_withdrawal": (
        "storage/earnings_guidance_current_prior_comparison_readiness_q4_2025_20260516/report.json",
        "storage/earnings_guidance_prior_guidance_exhibit_extraction_q4_2025_20260515/report.json",
    ),
    "cpi_inflation_release": (
        "storage/cpi_release_correlation_study_20260516/strict_summary.json",
        "storage/cpi_abnormal_release_correlation_study_20260516/abnormal_cpi_release_summary.json",
        "storage/cpi_surprise_correlation_study_20260516/cpi_surprise_summary.json",
        "storage/te_cpi_surprise_correlation_study_20260516/te_cpi_surprise_summary.json",
    ),
    "option_derivatives_abnormality": (
        "storage/option_activity_matched_control_study_20260515/report.json",
        "storage/option_activity_strict_filter_study_20260515/report.json",
        "storage/option_event_risk_amplifier_study_20260515/report.json",
    ),
}

FAMILY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "earnings_call_narrative_residual": ("earnings", "guidance", "outlook", "conference call", "revenue"),
    "equity_offering_dilution": ("offering", "secondary", "shelf", "atm", "convertible", "dilution"),
    "buyback_or_capital_return": ("buyback", "repurchase", "dividend", "capital return"),
    "mna_transaction": ("merger", "acquisition", "takeover", "deal", "bid", "to acquire"),
    "insider_or_ownership_change": ("insider", "13d", "13g", "activist", "stake", "ownership"),
    "legal_regulatory_investigation": ("investigation", "subpoena", "sec probe", "doj", "ftc", "lawsuit", "regulatory"),
    "accounting_restatement_or_fraud": ("restatement", "accounting", "fraud", "auditor", "material weakness"),
    "bankruptcy_or_restructuring": ("bankruptcy", "restructuring", "chapter 11", "liquidity crisis", "default"),
    "product_launch_or_failure": ("launch", "product", "recall", "delay", "defect", "safety"),
    "customer_contract_win_loss": ("contract", "customer", "supplier", "order", "win", "lost"),
    "management_change": ("ceo", "cfo", "resign", "resignation", "appoint", "management"),
    "analyst_rating_or_price_target_change": ("upgrade", "downgrade", "price target", "rating", "analyst", "initiates"),
    "supply_chain_disruption": ("supply chain", "supplier", "production", "logistics", "shortage", "factory"),
    "sector_regulation_policy": ("regulation", "policy", "tariff", "ban", "approval", "rule"),
    "commodity_or_input_cost_shock": ("oil", "gas", "commodity", "input cost", "copper", "steel"),
    "sector_demand_shock": ("demand", "shipment", "sales", "orders", "inventory", "industry"),
    "cpi_inflation_release": ("cpi", "inflation"),
    "fomc_rates_policy": ("fomc", "federal reserve", "fed", "interest rate", "centralbank"),
    "nfp_employment_release": ("non farm payroll", "payroll", "unemployment", "wage"),
    "treasury_yield_curve_shock": ("treasury", "yield", "curve", "rates", "bond"),
    "credit_liquidity_stress": ("credit", "liquidity", "spread", "funding", "stress"),
    "geopolitical_or_fiscal_shock": ("geopolitical", "war", "fiscal", "election", "sanction", "shutdown"),
    "price_action_pattern": ("breakout", "breakdown", "reversal", "support", "resistance"),
    "residual_market_structure_disturbance": ("halt", "volatility", "sweep", "imbalance", "market structure"),
    "microstructure_liquidity_disruption": ("spread", "depth", "liquidity", "halt", "imbalance"),
    "option_derivatives_abnormality": ("option", "options", "iv", "skew", "sweep", "open interest"),
}


@dataclass(frozen=True)
class LocalSourceProfile:
    alpaca_news_rows: int
    gdelt_news_rows: int
    sec_company_fact_rows: int
    trading_economics_rows: int
    trading_economics_expectation_rows: int
    bar_receipt_count: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True)
class EventFamilyCoverageRow:
    family_key: str
    routing_bucket: str
    mechanism_group: str
    priority: str
    coverage_status: str
    association_readiness_status: str
    local_candidate_count: int
    local_source_row_count: int
    local_source_routes: tuple[str, ...]
    existing_empirical_artifacts: tuple[str, ...]
    existing_empirical_artifact_count: int
    remaining_blocker_codes: tuple[str, ...]
    next_action: str
    final_conclusion_status: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        return {key: ";".join(value) if isinstance(value, tuple) else str(value) for key, value in row.items()}


@dataclass(frozen=True)
class EventFamilyEmpiricalCoverage:
    contract_type: str
    generated_at_utc: str
    source_precondition_path: str
    local_source_profile: LocalSourceProfile
    family_rows: tuple[EventFamilyCoverageRow, ...]
    provider_calls: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "family_count": len(self.family_rows),
            "coverage_status_counts": _counts(row.coverage_status for row in self.family_rows),
            "association_readiness_status_counts": _counts(row.association_readiness_status for row in self.family_rows),
            "families_with_local_candidates": [row.family_key for row in self.family_rows if row.local_candidate_count > 0],
            "families_with_existing_empirical_artifacts": [row.family_key for row in self.family_rows if row.existing_empirical_artifact_count > 0],
            "total_local_candidate_count": sum(row.local_candidate_count for row in self.family_rows),
            "local_source_profile": self.local_source_profile.to_dict(),
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
            "final_conclusion": "withheld_until_family_specific_empirical_association_studies_complete",
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "source_precondition_path": self.source_precondition_path,
            "local_source_profile": self.local_source_profile.to_dict(),
            "family_rows": [row.to_row() for row in self.family_rows],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _counts(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv_rows(pattern: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(glob.glob(pattern)):
        with open(path, encoding="utf-8", newline="") as handle:
            rows.extend(dict(row) for row in csv.DictReader(handle))
    return rows


def _parse_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _receipt_bar_count(root: Path) -> int:
    return len(glob.glob(str(root / "storage/monthly_backfill_v1/alpaca_bars/*/*/completion_receipt.json")))


def _source_profile(root: Path, source_rows: Mapping[str, list[dict[str, str]]]) -> LocalSourceProfile:
    return LocalSourceProfile(
        alpaca_news_rows=len(source_rows["alpaca_news"]),
        gdelt_news_rows=len(source_rows["gdelt_news"]),
        sec_company_fact_rows=len(source_rows["sec_company_fact"]),
        trading_economics_rows=len(source_rows["trading_economics"]),
        trading_economics_expectation_rows=sum(
            1 for row in source_rows["trading_economics"] if row.get("actual") and (row.get("consensus") or row.get("te_forecast"))
        ),
        bar_receipt_count=_receipt_bar_count(root),
    )


def _is_iso_like_event_row(row: Mapping[str, str]) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}T", str(row.get("event_time") or "")))


def _load_source_rows(root: Path) -> dict[str, list[dict[str, str]]]:
    base = root / "storage/monthly_backfill"
    te_rows = _read_csv_rows(str(base / "trading_economics_calendar_web/*/runs/*/saved/trading_economics_calendar_event.csv"))
    return {
        "alpaca_news": _read_csv_rows(str(base / "alpaca_news/*/runs/*/saved/equity_news.csv")),
        "gdelt_news": _read_csv_rows(str(base / "gdelt_news/*/runs/*/saved/gdelt_article.csv")),
        "sec_company_fact": _read_csv_rows(str(base / "sec_company_financials/*/runs/*/saved/sec_company_fact.csv")),
        "trading_economics": [row for row in te_rows if _is_iso_like_event_row(row)],
    }


def _text(row: Mapping[str, str], fields: Sequence[str]) -> str:
    return " ".join(str(row.get(field) or "") for field in fields).lower()


def _keyword_count(rows: Sequence[Mapping[str, str]], fields: Sequence[str], keywords: Sequence[str]) -> int:
    if not rows or not keywords:
        return 0
    patterns = [re.compile(re.escape(keyword.lower())) for keyword in keywords]
    count = 0
    for row in rows:
        text = _text(row, fields)
        if any(pattern.search(text) for pattern in patterns):
            count += 1
    return count


def _artifact_exists(path: str, model_root: Path) -> bool:
    resolved = Path(path)
    if not resolved.is_absolute():
        resolved = model_root / resolved
    return resolved.exists()


def _artifact_refs(family: str, model_root: Path) -> tuple[str, ...]:
    return tuple(ref for ref in EXISTING_EMPIRICAL_ARTIFACTS.get(family, ()) if _artifact_exists(ref, model_root))


def _source_routes(packet: Mapping[str, Any]) -> tuple[str, ...]:
    family = str(packet.get("family_key") or "")
    routing = str(packet.get("routing_bucket") or "")
    mechanism = str(packet.get("mechanism_group") or "")
    routes: list[str] = []
    if routing in {"symbol_news", "sector_news", "macro_news"}:
        routes.extend(["alpaca_news", "gdelt_news"])
    if routing == "sec_filing" or mechanism in {"capital_structure", "capital_allocation", "corporate_action", "ownership_governance", "legal_regulatory", "distress"}:
        routes.append("sec_company_financials")
    if routing == "macro_data" or mechanism.startswith("macro") or family in {"cpi_inflation_release", "nfp_employment_release", "fomc_rates_policy"}:
        routes.append("trading_economics_calendar_web")
    if family.startswith("earnings_guidance") or routing == "earnings_guidance":
        routes.extend(["earnings_guidance_artifacts", "sec_company_financials", "calendar_discovery"])
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        routes.extend(["local_price_bars", "option_activity_artifacts"])
    return tuple(dict.fromkeys(routes))


def _candidate_count(packet: Mapping[str, Any], rows: Mapping[str, list[dict[str, str]]]) -> int:
    family = str(packet.get("family_key") or "")
    routing = str(packet.get("routing_bucket") or "")
    keywords = FAMILY_KEYWORDS.get(family, ())
    if family == "earnings_guidance_scheduled_shell":
        return 12
    if family in {"earnings_guidance_result_metrics", "earnings_guidance_raise_cut_or_withdrawal"}:
        return 12
    if family == "cpi_inflation_release":
        return _keyword_count(rows["trading_economics"], ("event", "source_event_type"), keywords)
    if family == "nfp_employment_release":
        return _keyword_count(rows["trading_economics"], ("event", "source_event_type"), keywords)
    if family == "fomc_rates_policy":
        return _keyword_count(rows["trading_economics"], ("event", "source_event_type"), keywords) + _keyword_count(
            rows["gdelt_news"], ("title", "source_theme_tags", "organizations"), keywords
        )
    if routing in {"symbol_news", "sector_news", "macro_news"}:
        return _keyword_count(rows["alpaca_news"], ("timeline_headline", "summary"), keywords) + _keyword_count(
            rows["gdelt_news"], ("title", "source_theme_tags", "organizations", "persons", "locations"), keywords
        )
    if routing == "sec_filing":
        # Current local SEC monthly artifact is company-facts, not event filings. Count is deliberately zero until a family parser exists.
        return 0
    if routing in {"price_action", "equity_abnormal_activity", "option_abnormal_activity"}:
        return len(EXISTING_EMPIRICAL_ARTIFACTS.get(family, ()))
    return 0


def _source_row_count(routes: Sequence[str], profile: LocalSourceProfile) -> int:
    total = 0
    for route in routes:
        if route == "alpaca_news":
            total += profile.alpaca_news_rows
        elif route == "gdelt_news":
            total += profile.gdelt_news_rows
        elif route == "sec_company_financials":
            total += profile.sec_company_fact_rows
        elif route == "trading_economics_calendar_web":
            total += profile.trading_economics_rows
        elif route == "local_price_bars":
            total += profile.bar_receipt_count
    return total


def _coverage_status(family: str, candidate_count: int, artifacts: Sequence[str], blockers: Sequence[str]) -> str:
    if family == "option_derivatives_abnormality":
        return "existing_empirical_studies_deferred_low_signal"
    if family == "cpi_inflation_release":
        return "existing_empirical_studies_risk_only_needs_canonical_history"
    if family == "earnings_guidance_scheduled_shell":
        return "existing_empirical_study_underpowered_risk_shell"
    if "pit_expectation_or_comparable_baseline_required" in blockers:
        return "blocked_missing_pit_expectation_or_comparable_baseline"
    if "residual_over_base_state_required" in blockers:
        return "blocked_missing_residual_detector"
    if "liquidity_depth_evidence_required" in blockers:
        return "blocked_missing_liquidity_depth_evidence"
    if artifacts:
        return "existing_empirical_artifact_present_not_final"
    if candidate_count > 0:
        return "local_candidates_found_interpretation_required"
    return "no_local_candidate_events_found_under_current_sources"


def _readiness_status(family: str, coverage_status: str, blockers: Sequence[str]) -> str:
    if family == "option_derivatives_abnormality":
        return "not_ready_revise_abnormality_definition_before_retest"
    if family == "cpi_inflation_release":
        return "partial_ready_risk_only_after_fuller_te_history"
    if family == "earnings_guidance_scheduled_shell":
        return "partial_ready_expand_shell_sample_controls"
    if coverage_status.startswith("blocked_missing_pit"):
        return "not_ready_build_pit_baseline_first"
    if coverage_status == "blocked_missing_residual_detector":
        return "not_ready_build_residual_detector_first"
    if coverage_status == "blocked_missing_liquidity_depth_evidence":
        return "not_ready_build_liquidity_depth_route_first"
    if coverage_status == "local_candidates_found_interpretation_required":
        return "candidate_ready_for_interpretation_then_association"
    return "not_ready_expand_source_or_parser_first"


def _next_action(packet: Mapping[str, Any], coverage_status: str, candidate_count: int) -> str:
    family = str(packet.get("family_key") or "")
    if coverage_status == "local_candidates_found_interpretation_required":
        return "Interpret local candidate events, deduplicate canonical events, then build matched-control price/path labels."
    if coverage_status == "no_local_candidate_events_found_under_current_sources":
        return "Add or backfill the accepted source/parser route for this family before association measurement."
    if coverage_status.startswith("blocked_missing_pit"):
        return "Persist PIT expectation/comparable baseline artifacts before empirical association."
    if coverage_status == "blocked_missing_residual_detector":
        return "Implement residual-over-base-state detector before event labels are accepted."
    if coverage_status == "blocked_missing_liquidity_depth_evidence":
        return "Build liquidity/depth/execution-risk evidence before directional price labels."
    if family == "cpi_inflation_release":
        return "Complete fuller TE expectation-history route and rerun CPI surprise association using canonical rows."
    if family == "option_derivatives_abnormality":
        return "Revise abnormality definition before retesting matched controls."
    return str(packet.get("next_empirical_action") or "Run family-specific empirical association study.")


def build_event_family_empirical_coverage(
    *,
    precondition_path: Path = DEFAULT_PRECONDITION_PATH,
    trading_data_root: Path = DEFAULT_TRADING_DATA_ROOT,
    model_root: Path = Path("."),
    generated_at_utc: str | None = None,
) -> EventFamilyEmpiricalCoverage:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    source_rows = _load_source_rows(trading_data_root)
    profile = _source_profile(trading_data_root, source_rows)
    payload = _read_json(precondition_path)
    family_rows: list[EventFamilyCoverageRow] = []
    for packet in payload.get("packets", []):
        family = str(packet.get("family_key") or "")
        blockers = tuple(str(item) for item in packet.get("remaining_blocker_codes", []) if str(item))
        artifacts = _artifact_refs(family, model_root.resolve())
        routes = _source_routes(packet)
        candidate_count = _candidate_count(packet, source_rows)
        coverage = _coverage_status(family, candidate_count, artifacts, blockers)
        readiness = _readiness_status(family, coverage, blockers)
        family_rows.append(
            EventFamilyCoverageRow(
                family_key=family,
                routing_bucket=str(packet.get("routing_bucket") or ""),
                mechanism_group=str(packet.get("mechanism_group") or ""),
                priority=str(packet.get("priority") or ""),
                coverage_status=coverage,
                association_readiness_status=readiness,
                local_candidate_count=candidate_count,
                local_source_row_count=_source_row_count(routes, profile),
                local_source_routes=routes,
                existing_empirical_artifacts=artifacts,
                existing_empirical_artifact_count=len(artifacts),
                remaining_blocker_codes=blockers,
                next_action=_next_action(packet, coverage, candidate_count),
                final_conclusion_status="withheld_not_final_association_judgment",
            )
        )
    return EventFamilyEmpiricalCoverage(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        source_precondition_path=str(precondition_path),
        local_source_profile=profile,
        family_rows=tuple(family_rows),
    )


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_empirical_coverage_artifacts(coverage: EventFamilyEmpiricalCoverage, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_empirical_coverage.json").write_text(
        json.dumps(coverage.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_empirical_coverage_summary.json").write_text(
        json.dumps(coverage.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(EventFamilyCoverageRow("", "", "", "", "", "", 0, 0, (), (), 0, (), "", "").csv_row().keys())
    _write_csv(output_dir / "event_family_empirical_coverage.csv", [row.csv_row() for row in coverage.family_rows], fieldnames=fields)
    _write_csv(
        output_dir / "event_family_next_empirical_actions.csv",
        [
            {
                "family_key": row.family_key,
                "coverage_status": row.coverage_status,
                "association_readiness_status": row.association_readiness_status,
                "local_candidate_count": row.local_candidate_count,
                "next_action": row.next_action,
            }
            for row in coverage.family_rows
        ],
        fieldnames=["family_key", "coverage_status", "association_readiness_status", "local_candidate_count", "next_action"],
    )
    (output_dir / "README.md").write_text(
        f"""# Event-family empirical coverage

Contract: `{coverage.contract_type}`

This artifact scans only existing local source/study artifacts for all {len(coverage.family_rows)} EventRiskGovernor families.

It reports local candidate coverage and association readiness, but it does not make final association judgments. It performs no provider calls, model training, activation, broker/account mutation, or artifact deletion.

Final conclusion: `{coverage.summary['final_conclusion']}`.
""",
        encoding="utf-8",
    )


def write_coverage(coverage: EventFamilyEmpiricalCoverage, *, output: TextIO) -> None:
    json.dump(coverage.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "EventFamilyCoverageRow",
    "EventFamilyEmpiricalCoverage",
    "build_event_family_empirical_coverage",
    "write_coverage",
    "write_empirical_coverage_artifacts",
]
