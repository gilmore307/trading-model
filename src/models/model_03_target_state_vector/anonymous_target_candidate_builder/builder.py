"""Anonymous target candidate builder for Layer 3 preprocessing.

The builder expands accepted Layer 2 sector/industry context rows plus
point-in-time exposure/target evidence into anonymous candidate rows. Real symbol
metadata is kept in a separate audit/routing payload; the model-facing
``anonymous_target_feature_vector`` is recursively checked for identity leakage.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
BUILDER_VERSION = "anonymous_target_candidate_builder_v1_contract"
MODEL_FACING_VECTOR = "anonymous_target_feature_vector"
ANONYMITY_PASS_STATES = {"pass", "watch", "fail"}
ELIGIBILITY_STATES = {"eligible", "watch", "excluded", "insufficient_data"}
ALLOWED_SECTOR_HANDOFF_STATES = {"selected", "watch"}
FORBIDDEN_MODEL_FACING_FIELD_FRAGMENTS = (
    "ticker",
    "symbol",
    "company",
    "issuer",
    "exchange",
    "figi",
    "isin",
    "cusip",
    "cik",
    "audit_symbol_ref",
    "routing_symbol_ref",
    "source_holding_ref",
    "source_stock_etf_exposure_ref",
    "future_return",
    "realized_pnl",
    "strategy",
    "option_contract",
    "entry_price",
    "position_size",
)
IDENTITY_VALUE_KEYS = {"symbol", "ticker", "company", "issuer", "exchange", "figi", "isin", "cusip", "cik", "audit_symbol_ref", "routing_symbol_ref"}
NUMERIC_TARGET_EVIDENCE_KEYS = (
    "target_return_5min",
    "target_return_15min",
    "target_return_60min",
    "target_return_390min",
    "target_realized_vol_15min",
    "target_realized_vol_60min",
    "target_atr_pct",
    "target_range_position",
    "target_relative_volume",
    "target_dollar_volume",
    "target_spread_bps",
    "target_vwap_distance_pct",
    "target_gap_pct",
    "target_abnormal_activity_score",
    "target_event_density_score",
    "target_borrow_cost_score",
    "target_shortability_score",
    "target_optionability_score",
    "target_beta_to_market",
    "target_beta_to_sector",
    "target_corr_to_market",
    "target_corr_to_sector",
)
SECTOR_PROJECTION_KEYS = (
    "2_sector_relative_direction_score",
    "2_sector_trend_quality_score",
    "2_sector_trend_stability_score",
    "2_sector_transition_risk_score",
    "2_market_context_support_score",
    "2_sector_breadth_confirmation_score",
    "2_sector_internal_dispersion_score",
    "2_sector_crowding_risk_score",
    "2_sector_liquidity_tradability_score",
    "2_sector_tradability_score",
    "2_sector_handoff_state",
    "2_sector_handoff_bias",
    "2_sector_handoff_rank",
    "2_state_quality_score",
    "2_coverage_score",
    "2_data_quality_score",
)
MARKET_PROJECTION_KEYS = (
    "1_market_direction_score",
    "1_market_trend_quality_score",
    "1_market_stability_score",
    "1_market_transition_risk_score",
    "1_market_risk_stress_score",
    "1_market_liquidity_support_score",
    "1_market_data_quality_score",
)
OUTPUT_COLUMNS = [
    "available_time",
    "target_candidate_id",
    "candidate_builder_version",
    "market_context_state_ref",
    "sector_context_state_ref",
    MODEL_FACING_VECTOR,
    "candidate_eligibility_state",
    "candidate_eligibility_reason_codes",
    "candidate_source_rank",
    "candidate_generation_reason_codes",
    "candidate_data_quality_score",
    "candidate_anonymity_check_state",
    "candidate_anonymity_check_payload_json",
    "metadata_payload_json",
]


@dataclass(frozen=True)
class CandidateBuildResult:
    rows: list[dict[str, Any]]
    anonymity_report: dict[str, Any]


def build_candidate_rows(
    *,
    sector_context_rows: Iterable[Mapping[str, Any]],
    exposure_rows: Iterable[Mapping[str, Any]],
    target_evidence_rows: Iterable[Mapping[str, Any]] = (),
    market_context_rows: Iterable[Mapping[str, Any]] = (),
    candidate_builder_version: str = BUILDER_VERSION,
    anonymity_min_bucket_k: int = 2,
    id_salt: str = "target_context_state_v1",
) -> list[dict[str, Any]]:
    """Build anonymous target candidate rows.

    ``target_candidate_id`` is a deterministic opaque row key, not a fitting
    feature. Real symbols are retained only under ``metadata_payload_json``.
    """

    return build_candidates(
        sector_context_rows=sector_context_rows,
        exposure_rows=exposure_rows,
        target_evidence_rows=target_evidence_rows,
        market_context_rows=market_context_rows,
        candidate_builder_version=candidate_builder_version,
        anonymity_min_bucket_k=anonymity_min_bucket_k,
        id_salt=id_salt,
    ).rows


def build_candidates(
    *,
    sector_context_rows: Iterable[Mapping[str, Any]],
    exposure_rows: Iterable[Mapping[str, Any]],
    target_evidence_rows: Iterable[Mapping[str, Any]] = (),
    market_context_rows: Iterable[Mapping[str, Any]] = (),
    candidate_builder_version: str = BUILDER_VERSION,
    anonymity_min_bucket_k: int = 2,
    id_salt: str = "target_context_state_v1",
) -> CandidateBuildResult:
    sectors = [_normalize_sector_row(row) for row in sector_context_rows]
    sectors = [row for row in sectors if row.get("2_sector_handoff_state") in ALLOWED_SECTOR_HANDOFF_STATES]
    exposures = [_normalize_exposure_row(row) for row in exposure_rows]
    target_evidence = _target_evidence_by_symbol(target_evidence_rows)
    market_by_time = _market_by_time(market_context_rows)

    provisional: list[dict[str, Any]] = []
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for sector in sectors:
        available_time = _row_time_iso(sector, preferred="available_time")
        sector_symbol = str(sector.get("sector_or_industry_symbol") or sector.get("candidate_symbol") or "").strip().upper()
        for exposure in _matching_exposures(exposures, available_time=available_time, sector_symbol=sector_symbol):
            routing_symbol = _routing_symbol(exposure)
            if not routing_symbol:
                continue
            key = (available_time, routing_symbol)
            evidence = target_evidence.get(key) or target_evidence.get(("", routing_symbol)) or {}
            market_context = market_by_time.get(available_time, {})
            row = _build_row(
                available_time=available_time,
                routing_symbol=routing_symbol,
                sector_row=sector,
                exposure_row=exposure,
                target_evidence_row=evidence,
                market_context_row=market_context,
                candidate_builder_version=candidate_builder_version,
                id_salt=id_salt,
            )
            existing = seen.get(key)
            if existing is None:
                seen[key] = row
                provisional.append(row)
            else:
                _merge_duplicate_candidate(existing, row)

    bucket_counts = Counter(_bucket_signature(row.get(MODEL_FACING_VECTOR, {})) for row in provisional)
    for row in provisional:
        check = validate_model_facing_vector(
            row.get(MODEL_FACING_VECTOR, {}),
            candidate_id=str(row.get("target_candidate_id")),
            bucket_count=bucket_counts[_bucket_signature(row.get(MODEL_FACING_VECTOR, {}))],
            min_bucket_k=anonymity_min_bucket_k,
        )
        row["candidate_anonymity_check_state"] = check["state"]
        row["candidate_anonymity_check_payload_json"] = check
        quality = _safe_float(row.get("candidate_data_quality_score"))
        if check["state"] == "fail":
            row["candidate_eligibility_state"] = "excluded"
            _append_reason(row, "3_ANONYMITY_CHECK_FAILED")
        elif check["state"] == "watch":
            _append_reason(row, "3_ANONYMITY_BUCKET_WATCH")
            if row.get("candidate_eligibility_state") == "eligible":
                row["candidate_eligibility_state"] = "watch"
        if quality is None or quality < 0.25:
            row["candidate_eligibility_state"] = "insufficient_data"
            _append_reason(row, "3_INSUFFICIENT_TARGET_EVIDENCE")

    return CandidateBuildResult(rows=provisional, anonymity_report=_anonymity_report(provisional))


def validate_model_facing_vector(vector: Any, *, candidate_id: str = "", bucket_count: int | None = None, min_bucket_k: int = 2) -> dict[str, Any]:
    """Recursively validate that a model-facing vector is identity-safe."""

    violations: list[str] = []
    suspicious_keys: list[str] = []
    suspicious_values: list[str] = []

    def walk(value: Any, path: str = "") -> None:
        if isinstance(value, Mapping):
            for key, nested in value.items():
                key_text = str(key)
                key_lower = key_text.lower()
                next_path = f"{path}.{key_text}" if path else key_text
                if any(fragment in key_lower for fragment in FORBIDDEN_MODEL_FACING_FIELD_FRAGMENTS):
                    violations.append(f"forbidden_model_facing_key:{next_path}")
                    suspicious_keys.append(next_path)
                walk(nested, next_path)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for index, nested in enumerate(value):
                walk(nested, f"{path}[{index}]")
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped and _looks_like_raw_identity(stripped):
                violations.append(f"raw_identity_like_value:{path}")
                suspicious_values.append(path)

    walk(vector)
    if candidate_id and _looks_like_raw_identity(candidate_id):
        violations.append("target_candidate_id_reveals_identity")
    if _contains_key(vector, "target_candidate_id"):
        violations.append("target_candidate_id_in_model_facing_vector")

    state = "pass"
    if violations:
        state = "fail"
    elif bucket_count is not None and bucket_count < min_bucket_k:
        state = "watch"
    return {
        "state": state,
        "violations": sorted(set(violations)),
        "suspicious_keys": sorted(set(suspicious_keys)),
        "suspicious_values": sorted(set(suspicious_values)),
        "bucket_count": bucket_count,
        "minimum_bucket_k": min_bucket_k,
        "checks": {
            "no_raw_identity_fields": not violations,
            "target_candidate_id_row_key_only": "target_candidate_id_in_model_facing_vector" not in violations,
            "structural_bucket_k_anonymity": bucket_count is None or bucket_count >= min_bucket_k,
            "no_future_or_realized_pnl_fields": not any("future_return" in item or "realized_pnl" in item for item in violations),
        },
    }


def model_facing_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    payload = row.get(MODEL_FACING_VECTOR)
    if not isinstance(payload, Mapping):
        raise ValueError("anonymous target candidate row is missing anonymous_target_feature_vector")
    validate = validate_model_facing_vector(payload, candidate_id=str(row.get("target_candidate_id") or ""))
    if validate["state"] == "fail":
        raise ValueError(f"model-facing payload failed anonymity checks: {validate['violations']}")
    return dict(payload)


def _build_row(
    *,
    available_time: str,
    routing_symbol: str,
    sector_row: Mapping[str, Any],
    exposure_row: Mapping[str, Any],
    target_evidence_row: Mapping[str, Any],
    market_context_row: Mapping[str, Any],
    candidate_builder_version: str,
    id_salt: str,
) -> dict[str, Any]:
    sector_ref = _sector_ref(sector_row, available_time)
    market_ref = _market_ref(market_context_row, sector_row, available_time)
    candidate_id = _candidate_id(available_time, routing_symbol, sector_ref, candidate_builder_version, id_salt)
    vector = {
        "target_behavior_vector": _numeric_projection(target_evidence_row, NUMERIC_TARGET_EVIDENCE_KEYS[:8]),
        "target_liquidity_tradability_vector": _numeric_projection(target_evidence_row, NUMERIC_TARGET_EVIDENCE_KEYS[8:14]),
        "target_structural_bucket_vector": _structural_buckets(target_evidence_row, exposure_row),
        "sector_context_projection_vector": _projection(sector_row, SECTOR_PROJECTION_KEYS),
        "market_context_projection_vector": _projection(market_context_row, MARKET_PROJECTION_KEYS),
        "exposure_transmission_vector": _exposure_vector(exposure_row),
        "event_risk_context_vector": _numeric_projection(target_evidence_row, ("target_gap_pct", "target_abnormal_activity_score", "target_event_density_score")),
        "cost_and_constraint_vector": _cost_constraint_vector(target_evidence_row),
        "candidate_quality_vector": _quality_vector(sector_row, exposure_row, target_evidence_row),
    }
    quality = _quality_vector(sector_row, exposure_row, target_evidence_row)["candidate_data_quality_score"]
    eligibility, reasons = _eligibility(sector_row, exposure_row, target_evidence_row, quality)
    source_rank = _safe_int(sector_row.get("2_sector_handoff_rank") or exposure_row.get("candidate_source_rank") or exposure_row.get("source_rank"))
    return {
        "available_time": available_time,
        "target_candidate_id": candidate_id,
        "candidate_builder_version": candidate_builder_version,
        "market_context_state_ref": market_ref,
        "sector_context_state_ref": sector_ref,
        MODEL_FACING_VECTOR: vector,
        "candidate_eligibility_state": eligibility,
        "candidate_eligibility_reason_codes": ";".join(reasons),
        "candidate_source_rank": source_rank,
        "candidate_generation_reason_codes": "3_LAYER2_SECTOR_TRANSMISSION;3_TARGET_LOCAL_EVIDENCE_JOINED",
        "candidate_data_quality_score": quality,
        "candidate_anonymity_check_state": "pass",
        "candidate_anonymity_check_payload_json": {},
        "metadata_payload_json": {
            "audit_symbol_ref": str(exposure_row.get("audit_symbol_ref") or routing_symbol),
            "routing_symbol_ref": routing_symbol,
            "source_sector_or_industry_symbol": str(sector_row.get("sector_or_industry_symbol") or ""),
            "source_holding_ref": exposure_row.get("source_holding_ref"),
            "source_stock_etf_exposure_ref": exposure_row.get("source_stock_etf_exposure_ref"),
            "symbol_resolution_version": exposure_row.get("symbol_resolution_version"),
            "metadata_not_model_facing": True,
        },
    }


def _normalize_sector_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    output["available_time"] = _row_time_iso(row, preferred="available_time")
    if "sector_or_industry_symbol" in output:
        output["sector_or_industry_symbol"] = str(output["sector_or_industry_symbol"]).strip().upper()
    return output


def _normalize_exposure_row(row: Mapping[str, Any]) -> dict[str, Any]:
    output = dict(row)
    if output.get("available_time") or output.get("snapshot_time") or output.get("as_of_time"):
        output["available_time"] = _row_time_iso(row, preferred="available_time")
    return output


def _row_time_iso(row: Mapping[str, Any], *, preferred: str) -> str:
    return _parse_time(row.get(preferred) or row.get("snapshot_time") or row.get("as_of_time") or row.get("timestamp")).isoformat()


def _parse_time(value: Any) -> datetime:
    text = str(value or "").strip()
    if not text:
        raise ValueError("available_time/snapshot_time is required")
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _matching_exposures(exposures: Sequence[Mapping[str, Any]], *, available_time: str, sector_symbol: str) -> list[Mapping[str, Any]]:
    matches = []
    for row in exposures:
        row_time = str(row.get("available_time") or "")
        row_sector = str(row.get("sector_or_industry_symbol") or row.get("source_sector_or_industry_symbol") or row.get("holding_parent_symbol") or "").strip().upper()
        if row_time and row_time != available_time:
            continue
        if row_sector and sector_symbol and row_sector != sector_symbol:
            continue
        matches.append(row)
    return matches


def _routing_symbol(row: Mapping[str, Any]) -> str:
    return str(row.get("routing_symbol_ref") or row.get("audit_symbol_ref") or row.get("symbol") or row.get("ticker") or "").strip().upper()


def _candidate_id(available_time: str, routing_symbol: str, sector_ref: str | None, version: str, salt: str) -> str:
    digest = hashlib.sha256(json.dumps([available_time, routing_symbol, sector_ref, version, salt], separators=(",", ":")).encode("utf-8")).hexdigest()[:20]
    return f"tcand_{digest}"


def _sector_ref(row: Mapping[str, Any], available_time: str) -> str | None:
    explicit = str(row.get("sector_context_state_ref") or row.get("model_run_id") or "").strip()
    if explicit:
        return explicit
    symbol = str(row.get("sector_or_industry_symbol") or "").strip().upper()
    return f"model_02_sector_context:{available_time}:{symbol}" if symbol else None


def _market_ref(market_row: Mapping[str, Any], sector_row: Mapping[str, Any], available_time: str) -> str | None:
    explicit = str(market_row.get("market_context_state_ref") or market_row.get("model_run_id") or sector_row.get("market_context_state_ref") or "").strip()
    return explicit or f"model_01_market_regime:{available_time}"


def _market_by_time(rows: Iterable[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        result[_row_time_iso(row, preferred="available_time")] = row
    return result


def _target_evidence_by_symbol(rows: Iterable[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in rows:
        symbol = _routing_symbol(row)
        if not symbol:
            continue
        time_key = _row_time_iso(row, preferred="available_time") if (row.get("available_time") or row.get("snapshot_time") or row.get("timestamp")) else ""
        result[(time_key, symbol)] = row
    return result


def _projection(row: Mapping[str, Any], keys: Sequence[str]) -> dict[str, Any]:
    return {key: row.get(key) for key in keys if key in row and row.get(key) not in (None, "")}


def _numeric_projection(row: Mapping[str, Any], keys: Sequence[str]) -> dict[str, float]:
    return {key: value for key in keys if (value := _safe_float(row.get(key))) is not None}


def _exposure_vector(row: Mapping[str, Any]) -> dict[str, Any]:
    numeric = _numeric_projection(row, ("holding_weight", "exposure_weight", "sector_exposure_strength", "transmission_confidence", "holding_rank"))
    return {
        **numeric,
        "exposure_direction": _safe_category(row.get("exposure_direction"), allowed={"long", "short", "net_long", "net_short", "mixed", "unknown"}),
        "source_kind": _safe_category(row.get("source_kind") or row.get("candidate_source_kind"), allowed={"etf_holding", "stock_etf_exposure", "sector_proxy", "unknown"}),
    }


def _structural_buckets(target_row: Mapping[str, Any], exposure_row: Mapping[str, Any]) -> dict[str, Any]:
    dollar_volume = _safe_float(target_row.get("target_dollar_volume") or exposure_row.get("dollar_volume"))
    spread = _safe_float(target_row.get("target_spread_bps") or exposure_row.get("spread_bps"))
    volatility = _safe_float(target_row.get("target_atr_pct") or target_row.get("target_realized_vol_15min"))
    price = _safe_float(target_row.get("target_price") or exposure_row.get("price"))
    exposure = _safe_float(exposure_row.get("sector_exposure_strength") or exposure_row.get("exposure_weight") or exposure_row.get("holding_weight"))
    return {
        "liquidity_bucket": _bucket(dollar_volume, [(1_000_000, "low"), (10_000_000, "medium"), (100_000_000, "high")], "very_high"),
        "spread_cost_bucket": _bucket(spread, [(10, "tight"), (30, "normal"), (75, "wide")], "very_wide"),
        "volatility_bucket": _bucket(volatility, [(0.01, "low"), (0.03, "medium"), (0.07, "high")], "very_high"),
        "price_bucket": _bucket(price, [(10, "low_price"), (50, "mid_price"), (200, "high_price")], "very_high_price"),
        "sector_exposure_strength_bucket": _bucket(exposure, [(0.005, "thin"), (0.02, "normal"), (0.05, "strong")], "concentrated"),
    }


def _cost_constraint_vector(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **_numeric_projection(row, ("target_spread_bps", "target_dollar_volume", "target_borrow_cost_score", "target_shortability_score", "target_optionability_score")),
        "constraint_state": _safe_category(row.get("constraint_state"), allowed={"clear", "watch", "blocked", "unknown"}),
    }


def _quality_vector(sector_row: Mapping[str, Any], exposure_row: Mapping[str, Any], target_row: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "has_layer2_sector_context": bool(sector_row),
        "has_exposure_transmission": bool(exposure_row),
        "has_target_local_evidence": bool(target_row),
        "has_target_liquidity": _safe_float(target_row.get("target_dollar_volume")) is not None or _safe_float(target_row.get("target_spread_bps")) is not None,
        "has_sector_quality": _safe_float(sector_row.get("2_state_quality_score")) is not None,
    }
    return {**checks, "candidate_data_quality_score": sum(checks.values()) / len(checks), "evidence_count": sum(checks.values())}


def _eligibility(sector_row: Mapping[str, Any], exposure_row: Mapping[str, Any], target_row: Mapping[str, Any], quality: float | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if sector_row.get("2_sector_handoff_state") not in ALLOWED_SECTOR_HANDOFF_STATES:
        return "excluded", ["3_LAYER2_SECTOR_NOT_SELECTED_OR_WATCH"]
    if not exposure_row:
        return "insufficient_data", ["3_MISSING_EXPOSURE_TRANSMISSION"]
    if quality is None or quality < 0.25:
        return "insufficient_data", ["3_LOW_CANDIDATE_EVIDENCE_COVERAGE"]
    if _safe_float(target_row.get("target_spread_bps")) is not None and (_safe_float(target_row.get("target_spread_bps")) or 0) >= 150:
        reasons.append("3_WIDE_SPREAD_WATCH")
        return "watch", reasons
    return ("eligible" if quality >= 0.5 else "watch"), ["3_LAYER2_TRANSMISSION_TARGET_CANDIDATE"]


def _merge_duplicate_candidate(existing: dict[str, Any], incoming: Mapping[str, Any]) -> None:
    _append_reason(existing, "3_DUPLICATE_CANDIDATE_COLLAPSED")
    metadata = existing.setdefault("metadata_payload_json", {})
    sources = metadata.setdefault("collapsed_source_refs", [])
    incoming_meta = incoming.get("metadata_payload_json") if isinstance(incoming.get("metadata_payload_json"), Mapping) else {}
    sources.append({
        "source_sector_or_industry_symbol": incoming_meta.get("source_sector_or_industry_symbol"),
        "source_holding_ref": incoming_meta.get("source_holding_ref"),
        "source_stock_etf_exposure_ref": incoming_meta.get("source_stock_etf_exposure_ref"),
    })


def _append_reason(row: dict[str, Any], reason: str) -> None:
    current = [item for item in str(row.get("candidate_eligibility_reason_codes") or "").split(";") if item]
    if reason not in current:
        current.append(reason)
    row["candidate_eligibility_reason_codes"] = ";".join(current)


def _bucket(value: float | None, thresholds: Sequence[tuple[float, str]], fallback: str) -> str:
    if value is None:
        return "unknown"
    for threshold, label in thresholds:
        if value < threshold:
            return label
    return fallback


def _bucket_signature(vector: Any) -> str:
    if not isinstance(vector, Mapping):
        return "missing"
    buckets = vector.get("target_structural_bucket_vector")
    if not isinstance(buckets, Mapping):
        return "missing"
    return json.dumps(buckets, sort_keys=True, separators=(",", ":"), default=str)


def _contains_key(value: Any, key_name: str) -> bool:
    if isinstance(value, Mapping):
        return any(str(key) == key_name or _contains_key(nested, key_name) for key, nested in value.items())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_key(item, key_name) for item in value)
    return False


def _looks_like_raw_identity(value: str) -> bool:
    text = value.strip()
    if text.startswith("tcand_"):
        return False
    if len(text) <= 5 and text.replace(".", "").isalpha() and text.upper() == text:
        return True
    return any(marker in text.lower() for marker in (" inc", " corp", " class ", " nasdaq", " nyse"))


def _safe_category(value: Any, *, allowed: set[str]) -> str:
    text = str(value or "unknown").strip().lower()
    return text if text in allowed else "unknown"


def _safe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_int(value: Any) -> int | None:
    parsed = _safe_float(value)
    return None if parsed is None else int(parsed)


def _anonymity_report(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    states = Counter(str(row.get("candidate_anonymity_check_state")) for row in rows)
    return {
        "candidate_count": len(rows),
        "anonymity_state_counts": dict(sorted(states.items())),
        "failed_candidate_count": states.get("fail", 0),
        "watch_candidate_count": states.get("watch", 0),
        "model_facing_vector": MODEL_FACING_VECTOR,
        "metadata_separation": "audit/routing refs remain only in metadata_payload_json",
    }
