"""7-day, 14-day, and 30-day Cash Forecasting Engine for CashTrace."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from financial_engine.dead_zone_detector import detect_dead_zones
from financial_engine.root_cause_analyzer import attach_root_causes_to_dead_zones

FORECAST_CATEGORIES = (
    "KNOWN_SCHEDULED",
    "ESTIMATED_RECURRING",
    "ESTIMATED_BASELINE",
)


def _next_monthly_date(d: date, after_date: date) -> date:
    """Compute the next monthly occurrence of `d` strictly after `after_date`."""
    candidate = d
    while candidate <= after_date:
        year = candidate.year + (candidate.month // 12)
        month = (candidate.month % 12) + 1
        # Clamp day to valid month length
        for day_try in (d.day, 28, 29, 30):
            try:
                candidate = date(year, month, min(d.day, day_try))
                break
            except ValueError:
                continue
        else:
            candidate = date(year, month, 28)
    return candidate


def generate_forecasts(
    normalized_records: list[dict[str, Any]],
    starting_cash: float,
    as_of_date: date | str,
    safety_reserve: float = 100000.0,
    historical_days_count: int = 0,
    horizons: tuple[int, ...] = (7, 14, 30),
) -> dict[str, Any]:
    """
    Generate deterministic 7-day, 14-day, and 30-day cash forecasts.

    Forecast categories:
    - KNOWN_SCHEDULED: Unpaid/scheduled transactions (and any rows with effective_date > as_of_date).
    - ESTIMATED_RECURRING: Projected next-cycle occurrences of recurring historical items.
    - ESTIMATED_BASELINE: Graceful baseline estimation when >= 14 days of history exist
      (degrades gracefully to 0 when insufficient history exists).
    """
    as_of_dt = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date
    max_horizon = max(horizons) if horizons else 30
    end_dt = as_of_dt + timedelta(days=max_horizon)

    forecast_events: list[dict[str, Any]] = []

    # 1. KNOWN_SCHEDULED events
    scheduled_keys: set[tuple[str, str, str]] = set()
    for r in normalized_records:
        eff_dt = date.fromisoformat(r["effective_date"])
        is_future_settled = r["ledger_state"] == "SETTLED" and eff_dt > as_of_dt
        is_scheduled = r["ledger_state"] == "SCHEDULED"

        if not (is_scheduled or is_future_settled):
            continue

        # Overdue unpaid items: if due_date <= as_of_date, project collection/payout
        # at a deterministic 3-day grace offset after as_of_date (unless overridden by simulation)
        if is_scheduled and eff_dt <= as_of_dt:
            projected_dt = r.get("simulated_date")
            if projected_dt:
                target_dt = date.fromisoformat(projected_dt)
            else:
                target_dt = as_of_dt + timedelta(days=3)
        else:
            target_dt = eff_dt

        if as_of_dt < target_dt <= end_dt:
            ev = dict(r)
            ev["effective_date"] = target_dt.isoformat()
            ev["forecast_category"] = "KNOWN_SCHEDULED"
            forecast_events.append(ev)
            scheduled_keys.add(
                (
                    r["type"],
                    (r.get("category") or "").lower(),
                    (r.get("counterparty") or "").lower(),
                )
            )

    # 2. ESTIMATED_RECURRING events (from historical settled recurring rows)
    historical_recurring = [
        r
        for r in normalized_records
        if r["ledger_state"] == "SETTLED"
        and date.fromisoformat(r["effective_date"]) <= as_of_dt
        and r.get("is_recurring")
    ]
    # Group by (type, category, counterparty) and take the most recent occurrence
    latest_recurring: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in historical_recurring:
        key = (
            r["type"],
            (r.get("category") or "").lower(),
            (r.get("counterparty") or "").lower(),
        )
        if key not in latest_recurring or r["effective_date"] > latest_recurring[key]["effective_date"]:
            latest_recurring[key] = r

    for (tx_type, cat_lower, cp_lower), rec_row in latest_recurring.items():
        if (tx_type, cat_lower, cp_lower) in scheduled_keys:
            continue
        last_dt = date.fromisoformat(rec_row["effective_date"])
        next_dt = _next_monthly_date(last_dt, as_of_dt)
        if as_of_dt < next_dt <= end_dt:
            forecast_events.append(
                {
                    "row_id": f"REC-{rec_row['row_id']}",
                    "raw_date": next_dt.isoformat(),
                    "date": next_dt.isoformat(),
                    "due_date": next_dt.isoformat(),
                    "actual_payment_date": None,
                    "effective_date": next_dt.isoformat(),
                    "type": rec_row["type"],
                    "amount": round(float(rec_row["amount"]), 2),
                    "signed_amount": round(float(rec_row["signed_amount"]), 2),
                    "category": rec_row.get("category") or "Recurring",
                    "counterparty": rec_row.get("counterparty") or "",
                    "description": f"Estimated recurring: {rec_row.get('description') or rec_row.get('category')}",
                    "ledger_state": "SCHEDULED",
                    "is_recurring": True,
                    "forecast_category": "ESTIMATED_RECURRING",
                }
            )

    # 3. ESTIMATED_BASELINE (graceful degradation if < 14 historical days)
    settled_non_recurring = [
        r
        for r in normalized_records
        if r["ledger_state"] == "SETTLED"
        and date.fromisoformat(r["effective_date"]) <= as_of_dt
        and not r.get("is_recurring")
    ]
    has_sufficient_history = historical_days_count >= 14 and len(settled_non_recurring) >= 4
    daily_baseline_inflow = 0.0
    daily_baseline_outflow = 0.0

    # Only use baseline extrapolation if there are NO explicit scheduled items provided,
    # so we never double-count explicit invoices/bills in hybrid ledger mode.
    has_explicit_scheduled = any(
        e["forecast_category"] == "KNOWN_SCHEDULED" for e in forecast_events
    )
    if has_sufficient_history and not has_explicit_scheduled:
        hist_in = sum(float(r["amount"]) for r in settled_non_recurring if r["type"] == "inflow")
        hist_out = sum(float(r["amount"]) for r in settled_non_recurring if r["type"] == "outflow")
        daily_baseline_inflow = round(hist_in / historical_days_count, 2)
        daily_baseline_outflow = round(hist_out / historical_days_count, 2)

    # Build daily timeline for max_horizon days
    events_by_date: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for ev in forecast_events:
        events_by_date[date.fromisoformat(ev["effective_date"])].append(ev)

    full_timeline: list[dict[str, Any]] = []
    running_cash = round(float(starting_cash), 2)

    for offset in range(1, max_horizon + 1):
        curr_dt = as_of_dt + timedelta(days=offset)
        day_events = events_by_date.get(curr_dt, [])

        known_in = sum(
            float(e["amount"])
            for e in day_events
            if e["type"] == "inflow" and e["forecast_category"] == "KNOWN_SCHEDULED"
        )
        known_out = sum(
            float(e["amount"])
            for e in day_events
            if e["type"] == "outflow" and e["forecast_category"] == "KNOWN_SCHEDULED"
        )
        rec_in = sum(
            float(e["amount"])
            for e in day_events
            if e["type"] == "inflow" and e["forecast_category"] == "ESTIMATED_RECURRING"
        )
        rec_out = sum(
            float(e["amount"])
            for e in day_events
            if e["type"] == "outflow" and e["forecast_category"] == "ESTIMATED_RECURRING"
        )

        day_open = running_cash
        day_in = round(known_in + rec_in + daily_baseline_inflow, 2)
        day_out = round(known_out + rec_out + daily_baseline_outflow, 2)
        day_net = round(day_in - day_out, 2)
        day_close = round(day_open + day_net, 2)

        full_timeline.append(
            {
                "date": curr_dt.isoformat(),
                "opening_cash": day_open,
                "inflows": day_in,
                "outflows": day_out,
                "net_movement": day_net,
                "closing_cash": day_close,
                "below_safety_reserve": day_close < safety_reserve,
                "breakdown": {
                    "KNOWN_SCHEDULED": {
                        "inflows": round(known_in, 2),
                        "outflows": round(known_out, 2),
                    },
                    "ESTIMATED_RECURRING": {
                        "inflows": round(rec_in, 2),
                        "outflows": round(rec_out, 2),
                    },
                    "ESTIMATED_BASELINE": {
                        "inflows": daily_baseline_inflow,
                        "outflows": daily_baseline_outflow,
                    },
                },
                "transaction_ids": [e["row_id"] for e in day_events],
            }
        )
        running_cash = day_close

    # Slice per horizon (7, 14, 30)
    combined_records = normalized_records + [
        e for e in forecast_events if e["forecast_category"] == "ESTIMATED_RECURRING"
    ]
    horizons_output: dict[str, Any] = {}
    for h in horizons:
        slice_days = full_timeline[:h]
        h_inflows = round(sum(d["inflows"] for d in slice_days), 2)
        h_outflows = round(sum(d["outflows"] for d in slice_days), 2)
        h_end_cash = slice_days[-1]["closing_cash"] if slice_days else round(float(starting_cash), 2)
        h_min_cash = min((d["closing_cash"] for d in slice_days), default=h_end_cash)

        raw_dz = detect_dead_zones(
            slice_days,
            safety_reserve=safety_reserve,
            min_consecutive_days=2,
            is_forecast=True,
            id_prefix=f"DZ-F{h}D",
        )
        enriched_dz = attach_root_causes_to_dead_zones(raw_dz, combined_records)

        horizons_output[f"{h}_days"] = {
            "horizon_days": h,
            "start_date": slice_days[0]["date"] if slice_days else as_of_dt.isoformat(),
            "end_date": slice_days[-1]["date"] if slice_days else as_of_dt.isoformat(),
            "starting_cash": round(float(starting_cash), 2),
            "total_projected_inflows": h_inflows,
            "total_projected_outflows": h_outflows,
            "ending_projected_cash": h_end_cash,
            "min_projected_cash": h_min_cash,
            "dead_zones_count": len(enriched_dz),
            "dead_zones": enriched_dz,
            "timeline": slice_days,
        }

    return {
        "as_of_date": as_of_dt.isoformat(),
        "starting_cash": round(float(starting_cash), 2),
        "safety_reserve": round(float(safety_reserve), 2),
        "baseline_mode": "EXTRAPOLATED" if (has_sufficient_history and not has_explicit_scheduled) else "KNOWN_AND_RECURRING_ONLY",
        "degraded_gracefully": not has_sufficient_history,
        "scheduled_events_count": len([e for e in forecast_events if e["forecast_category"] == "KNOWN_SCHEDULED"]),
        "recurring_events_count": len([e for e in forecast_events if e["forecast_category"] == "ESTIMATED_RECURRING"]),
        "horizons": horizons_output,
    }

