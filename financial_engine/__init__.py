"""Deterministic Financial Engine for CashTrace MSME Dead Zone Detection."""

from __future__ import annotations

from datetime import date
from typing import Any

from financial_engine.dead_zone_detector import compute_severity_and_score, detect_dead_zones
from financial_engine.forecaster import generate_forecasts
from financial_engine.normalizer import normalize_records
from financial_engine.reconstructor import reconstruct_cash_timeline
from financial_engine.root_cause_analyzer import (
    analyze_dead_zone_root_causes,
    attach_root_causes_to_dead_zones,
)
from financial_engine.simulator import run_what_if_simulation
from financial_engine.validator import ValidationError, parse_csv_content, validate_records

DEFAULT_SAFETY_RESERVE = 100000.0


def run_full_analysis(
    raw_records: list[dict[str, Any]],
    opening_cash: float,
    safety_reserve: float = DEFAULT_SAFETY_RESERVE,
    as_of_date: date | str | None = None,
) -> dict[str, Any]:
    """
    Execute the complete deterministic CashTrace pipeline:
    Validate -> Normalize -> Reconstruct -> Detect Dead Zones -> Root Causes -> Forecast.
    """
    validated = validate_records(raw_records)
    normalized, resolved_as_of = normalize_records(validated, as_of_date=as_of_date)

    reconstruction = reconstruct_cash_timeline(
        normalized_records=normalized,
        opening_cash=opening_cash,
        as_of_date=resolved_as_of,
        safety_reserve=safety_reserve,
    )

    raw_dead_zones = detect_dead_zones(
        timeline=reconstruction["timeline"],
        safety_reserve=safety_reserve,
        min_consecutive_days=2,
        is_forecast=False,
        id_prefix="DZ",
    )
    dead_zones = attach_root_causes_to_dead_zones(raw_dead_zones, normalized)

    forecasts = generate_forecasts(
        normalized_records=normalized,
        starting_cash=reconstruction["final_closing_cash"],
        as_of_date=resolved_as_of,
        safety_reserve=safety_reserve,
        historical_days_count=reconstruction["days_count"],
        horizons=(7, 14, 30),
    )

    # Aggregate unique root causes across historical + 30d forecast dead zones
    all_dead_zones = dead_zones + forecasts["horizons"]["30_days"]["dead_zones"]
    all_root_causes: list[dict[str, Any]] = []
    for dz in all_dead_zones:
        for rc in dz.get("root_causes", []):
            rc_with_dz = dict(rc)
            rc_with_dz["dead_zone_id"] = dz["dead_zone_id"]
            rc_with_dz["is_forecast"] = dz.get("is_forecast", False)
            all_root_causes.append(rc_with_dz)

    settled_count = sum(1 for r in normalized if r["ledger_state"] == "SETTLED")
    scheduled_count = sum(1 for r in normalized if r["ledger_state"] == "SCHEDULED")
    overdue_count = sum(1 for r in normalized if r.get("is_overdue"))

    return {
        "as_of_date": resolved_as_of.isoformat(),
        "opening_cash": round(float(opening_cash), 2),
        "safety_reserve": round(float(safety_reserve), 2),
        "summary": {
            "total_transactions": len(normalized),
            "settled_transactions": settled_count,
            "scheduled_transactions": scheduled_count,
            "overdue_unpaid_transactions": overdue_count,
            "opening_cash": reconstruction["opening_cash"],
            "total_inflows": reconstruction["total_inflows"],
            "total_outflows": reconstruction["total_outflows"],
            "final_closing_cash": reconstruction["final_closing_cash"],
            "min_closing_cash": reconstruction["min_closing_cash"],
            "historical_dead_zones_count": len(dead_zones),
            "forecast_30d_dead_zones_count": forecasts["horizons"]["30_days"]["dead_zones_count"],
            "invariant_verified": reconstruction["invariant_verified"],
        },
        "normalized_transactions": normalized,
        "reconstruction": reconstruction,
        "timeline": reconstruction["timeline"],
        "dead_zones": dead_zones,
        "root_causes": all_root_causes,
        "forecasts": forecasts,
    }


__all__ = [
    "DEFAULT_SAFETY_RESERVE",
    "ValidationError",
    "analyze_dead_zone_root_causes",
    "attach_root_causes_to_dead_zones",
    "compute_severity_and_score",
    "detect_dead_zones",
    "generate_forecasts",
    "normalize_records",
    "parse_csv_content",
    "reconstruct_cash_timeline",
    "run_full_analysis",
    "run_what_if_simulation",
    "validate_records",
]
