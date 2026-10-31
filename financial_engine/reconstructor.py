"""Historical daily cash timeline reconstruction for CashTrace."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any


def reconstruct_cash_timeline(
    normalized_records: list[dict[str, Any]],
    opening_cash: float,
    as_of_date: date | str,
    safety_reserve: float = 100000.0,
) -> dict[str, Any]:
    """
    Reconstruct a deterministic daily cash timeline up to `as_of_date`.

    Rules:
    - Only SETTLED rows with `effective_date <= as_of_date` affect historical cash.
    - Unpaid/Scheduled rows (even if overdue) do NOT affect historical cash.
    - Enforces invariant: opening_cash + total_inflows - total_outflows == final_closing_cash.
    """
    if isinstance(as_of_date, str):
        as_of_dt = date.fromisoformat(as_of_date)
    else:
        as_of_dt = as_of_date

    settled_rows = [
        r
        for r in normalized_records
        if r.get("ledger_state") == "SETTLED"
        and date.fromisoformat(r["effective_date"]) <= as_of_dt
    ]

    if settled_rows:
        start_dt = min(date.fromisoformat(r["effective_date"]) for r in settled_rows)
    else:
        start_dt = as_of_dt

    # Group inflows and outflows by effective_date
    daily_inflows: dict[date, float] = defaultdict(float)
    daily_outflows: dict[date, float] = defaultdict(float)
    daily_tx_ids: dict[date, list[str]] = defaultdict(list)

    for row in settled_rows:
        eff_dt = date.fromisoformat(row["effective_date"])
        amt = round(float(row["amount"]), 2)
        if row["type"] == "inflow":
            daily_inflows[eff_dt] = round(daily_inflows[eff_dt] + amt, 2)
        else:
            daily_outflows[eff_dt] = round(daily_outflows[eff_dt] + amt, 2)
        daily_tx_ids[eff_dt].append(row["row_id"])

    timeline: list[dict[str, Any]] = []
    running_cash = round(float(opening_cash), 2)
    total_inflows = 0.0
    total_outflows = 0.0

    curr_dt = start_dt
    while curr_dt <= as_of_dt:
        day_open = running_cash
        day_in = round(daily_inflows.get(curr_dt, 0.0), 2)
        day_out = round(daily_outflows.get(curr_dt, 0.0), 2)
        day_net = round(day_in - day_out, 2)
        day_close = round(day_open + day_net, 2)

        total_inflows = round(total_inflows + day_in, 2)
        total_outflows = round(total_outflows + day_out, 2)

        timeline.append(
            {
                "date": curr_dt.isoformat(),
                "opening_cash": day_open,
                "inflows": day_in,
                "outflows": day_out,
                "net_movement": day_net,
                "closing_cash": day_close,
                "below_safety_reserve": day_close < safety_reserve,
                "transaction_ids": daily_tx_ids.get(curr_dt, []),
            }
        )
        running_cash = day_close
        curr_dt += timedelta(days=1)

    final_closing_cash = running_cash
    expected_closing = round(round(float(opening_cash), 2) + total_inflows - total_outflows, 2)
    if abs(final_closing_cash - expected_closing) > 0.01:
        raise RuntimeError(
            f"Cash invariant violated: {opening_cash} + {total_inflows} - {total_outflows} != {final_closing_cash}"
        )

    min_cash = min((d["closing_cash"] for d in timeline), default=final_closing_cash)
    max_cash = max((d["closing_cash"] for d in timeline), default=final_closing_cash)

    return {
        "start_date": start_dt.isoformat(),
        "end_date": as_of_dt.isoformat(),
        "as_of_date": as_of_dt.isoformat(),
        "days_count": len(timeline),
        "opening_cash": round(float(opening_cash), 2),
        "total_inflows": total_inflows,
        "total_outflows": total_outflows,
        "net_cash_flow": round(total_inflows - total_outflows, 2),
        "final_closing_cash": final_closing_cash,
        "min_closing_cash": min_cash,
        "max_closing_cash": max_cash,
        "invariant_verified": True,
        "timeline": timeline,
    }

