"""Deterministic Dead Zone Detection and Severity Scoring for CashTrace."""

from __future__ import annotations

from typing import Any

DOMAIN_TO_DB_SEVERITY = {
    "LOW": "low",
    "MEDIUM": "warning",
    "HIGH": "critical",
    "CRITICAL": "fatal",
}


def compute_severity_and_score(
    minimum_cash: float,
    safety_reserve: float,
    duration_days: int,
) -> tuple[str, float, float, float]:
    """
    Compute deterministic severity ('LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'),
    severity_score (0..100), absolute_shortfall, and shortfall_percentage.

    Formula:
    - absolute_shortfall = max(0, safety_reserve - minimum_cash)
    - shortfall_pct = (absolute_shortfall / safety_reserve * 100) if safety_reserve > 0 else 100.0
    - depth_component = min(70.0, shortfall_pct * 0.7) (up to 70 pts, or 75+ if minimum_cash < 0)
    - duration_component = min(30.0, (duration_days - 1) * 3.5)
    - severity_score = round(min(100.0, depth_component + duration_component), 1)
    - Thresholds:
        * CRITICAL if minimum_cash < 0 or severity_score >= 75
        * HIGH if shortfall_pct >= 50.0 or severity_score >= 50
        * MEDIUM if shortfall_pct >= 25.0 or severity_score >= 25
        * LOW otherwise
    """
    absolute_shortfall = round(max(0.0, safety_reserve - minimum_cash), 2)
    if safety_reserve > 0:
        shortfall_pct = round((absolute_shortfall / safety_reserve) * 100.0, 2)
    else:
        shortfall_pct = 100.0 if minimum_cash < 0 else 0.0

    if minimum_cash < 0:
        # Negative cash balance guarantees at least 75 base score
        overdraft_ratio = abs(minimum_cash) / max(safety_reserve, 1.0)
        depth_component = min(80.0, 70.0 + overdraft_ratio * 20.0)
    else:
        depth_component = min(70.0, shortfall_pct * 0.70)

    duration_component = min(30.0, max(0, duration_days - 1) * 3.5)
    severity_score = round(min(100.0, max(5.0, depth_component + duration_component)), 1)

    if minimum_cash < 0 or severity_score >= 75.0:
        severity = "CRITICAL"
        if severity_score < 75.0:
            severity_score = round(min(100.0, 75.0 + duration_component * 0.8), 1)
    elif shortfall_pct >= 50.0 or severity_score >= 50.0:
        severity = "HIGH"
    elif shortfall_pct >= 25.0 or severity_score >= 25.0:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return severity, severity_score, absolute_shortfall, shortfall_pct


def detect_dead_zones(
    timeline: list[dict[str, Any]],
    safety_reserve: float = 100000.0,
    min_consecutive_days: int = 2,
    is_forecast: bool = False,
    id_prefix: str = "DZ",
) -> list[dict[str, Any]]:
    """
    Scan a daily cash timeline and detect contiguous periods of at least
    `min_consecutive_days` (default 2) where `closing_cash < safety_reserve`.
    """
    dead_zones: list[dict[str, Any]] = []
    current_run: list[dict[str, Any]] = []

    def _finalize_run(run_days: list[dict[str, Any]], index: int) -> dict[str, Any]:
        start_date = run_days[0]["date"]
        end_date = run_days[-1]["date"]
        duration = len(run_days)
        min_day = min(run_days, key=lambda d: d["closing_cash"])
        minimum_cash = round(float(min_day["closing_cash"]), 2)

        severity, severity_score, abs_shortfall, shortfall_pct = compute_severity_and_score(
            minimum_cash=minimum_cash,
            safety_reserve=safety_reserve,
            duration_days=duration,
        )

        dz_id = f"{id_prefix}-{index:03d}"
        return {
            "dead_zone_id": dz_id,
            "start_date": start_date,
            "end_date": end_date,
            "duration": duration,
            "duration_days": duration,
            "minimum_cash": minimum_cash,
            "min_cash_date": min_day["date"],
            "safety_reserve": round(float(safety_reserve), 2),
            "absolute_shortfall": abs_shortfall,
            "shortfall_percentage": shortfall_pct,
            "severity": severity,
            "severity_score": severity_score,
            "db_severity": DOMAIN_TO_DB_SEVERITY[severity],
            "is_negative_cash": minimum_cash < 0,
            "is_forecast": is_forecast,
        }

    for day in timeline:
        if float(day["closing_cash"]) < safety_reserve:
            current_run.append(day)
        else:
            if len(current_run) >= min_consecutive_days:
                dead_zones.append(_finalize_run(current_run, len(dead_zones) + 1))
            current_run = []

    if len(current_run) >= min_consecutive_days:
        dead_zones.append(_finalize_run(current_run, len(dead_zones) + 1))

    return dead_zones

