"""Non-mutating What-If Scenario Simulator for CashTrace."""

from __future__ import annotations

import copy
from datetime import date, timedelta
from typing import Any

from financial_engine.dead_zone_detector import detect_dead_zones
from financial_engine.forecaster import generate_forecasts
from financial_engine.reconstructor import reconstruct_cash_timeline
from financial_engine.root_cause_analyzer import attach_root_causes_to_dead_zones


def _apply_single_intervention(
    records: list[dict[str, Any]],
    safety_reserve: float,
    as_of_dt: date,
    intervention: dict[str, Any],
) -> tuple[list[dict[str, Any]], float, dict[str, Any]]:
    """Apply a single intervention to a cloned list of normalized records."""
    raw_type = str(
        intervention.get("type")
        or intervention.get("action_type")
        or intervention.get("intervention_type")
        or ""
    ).strip().upper()

    target_id = (
        intervention.get("transaction_id")
        or intervention.get("row_id")
        or intervention.get("target_id")
    )
    target_ids: set[str] = set()
    if target_id:
        target_ids.add(str(target_id))
    if intervention.get("transaction_ids"):
        target_ids.update(str(tid) for tid in intervention["transaction_ids"])

    applied_log: dict[str, Any] = {"type": raw_type, "target_ids": sorted(target_ids)}

    # C. Safety reserve changed
    if raw_type in {"SAFETY_RESERVE_CHANGED", "CHANGE_SAFETY_RESERVE", "SAFETY_RESERVE"}:
        new_reserve = float(
            intervention.get("new_safety_reserve")
            if intervention.get("new_safety_reserve") is not None
            else intervention.get("safety_reserve", intervention.get("amount", safety_reserve))
        )
        applied_log["previous_safety_reserve"] = safety_reserve
        applied_log["new_safety_reserve"] = round(new_reserve, 2)
        return records, round(new_reserve, 2), applied_log

    # A. Customer payment earlier
    if raw_type in {"CUSTOMER_PAYMENT_EARLIER", "ACCELERATE_INFLOW", "INFLOW_EARLIER"}:
        days_earlier = int(intervention.get("days_earlier") or intervention.get("days") or 5)
        explicit_date_str = intervention.get("new_date") or intervention.get("target_date")

        candidates = [
            r
            for r in records
            if r["type"] == "inflow"
            and (not target_ids or r["row_id"] in target_ids)
        ]
        # If no specific target_id provided, pick delayed/unpaid inflows first
        if not target_ids:
            delayed = [
                r
                for r in candidates
                if r["ledger_state"] == "SCHEDULED" or r.get("delay_days", 0) > 0
            ]
            candidates = delayed or candidates[:1]

        modified_ids: list[str] = []
        for r in candidates:
            orig_eff = date.fromisoformat(r["effective_date"])
            if explicit_date_str:
                new_dt = date.fromisoformat(str(explicit_date_str))
            else:
                base_dt = (
                    date.fromisoformat(r["due_date"])
                    if r["ledger_state"] == "SCHEDULED" and r.get("due_date")
                    else orig_eff
                )
                new_dt = base_dt - timedelta(days=abs(days_earlier))

            r["effective_date"] = new_dt.isoformat()
            r["actual_payment_date"] = new_dt.isoformat()
            r["simulated_date"] = new_dt.isoformat()
            if new_dt <= as_of_dt:
                r["ledger_state"] = "SETTLED"
                r["is_historical"] = True
            else:
                r["ledger_state"] = "SCHEDULED"
                r["is_historical"] = False
            modified_ids.append(r["row_id"])

        applied_log["modified_transaction_ids"] = modified_ids
        return records, safety_reserve, applied_log

    # B. Supplier payment shifted or split
    if raw_type in {
        "SUPPLIER_PAYMENT_SHIFTED",
        "SUPPLIER_PAYMENT_SPLIT",
        "SUPPLIER_PAYMENT_SHIFT_OR_SPLIT",
        "DEFER_OUTFLOW",
        "SPLIT_OUTFLOW",
    }:
        shift_days = int(intervention.get("shift_days") or intervention.get("days") or 7)
        explicit_date_str = intervention.get("new_date") or intervention.get("target_date")
        splits = intervention.get("splits")
        split_count = int(intervention.get("split_count") or (2 if "SPLIT" in raw_type else 1))
        split_interval_days = int(intervention.get("split_interval_days") or shift_days or 7)

        candidates = [
            r
            for r in records
            if r["type"] == "outflow"
            and (not target_ids or r["row_id"] in target_ids)
        ]
        if not target_ids and candidates:
            # Pick the largest outflow by default
            candidates = [max(candidates, key=lambda x: float(x["amount"]))]

        target_set = {r["row_id"] for r in candidates}
        updated_records: list[dict[str, Any]] = []
        modified_ids: list[str] = []

        for r in records:
            if r["row_id"] not in target_set:
                updated_records.append(r)
                continue

            modified_ids.append(r["row_id"])
            orig_eff = date.fromisoformat(r["effective_date"])

            if splits and isinstance(splits, list):
                # Custom split array [{"date": "YYYY-MM-DD", "amount": 50000}, ...]
                for idx, sp in enumerate(splits, start=1):
                    part = copy.deepcopy(r)
                    part_amt = round(float(sp["amount"]), 2)
                    part_dt = (
                        date.fromisoformat(str(sp["date"]))
                        if sp.get("date")
                        else orig_eff + timedelta(days=(idx - 1) * split_interval_days)
                    )
                    part["row_id"] = f"{r['row_id']}-S{idx}"
                    part["amount"] = part_amt
                    part["signed_amount"] = -part_amt
                    part["effective_date"] = part_dt.isoformat()
                    part["simulated_date"] = part_dt.isoformat()
                    part["ledger_state"] = "SETTLED" if part_dt <= as_of_dt else "SCHEDULED"
                    part["is_historical"] = part_dt <= as_of_dt
                    updated_records.append(part)
            elif split_count > 1:
                # Equal split into `split_count` installments spaced by `split_interval_days`
                total_amt = round(float(r["amount"]), 2)
                base_part = round(total_amt / split_count, 2)
                remainder = round(total_amt - base_part * (split_count - 1), 2)

                for idx in range(split_count):
                    part = copy.deepcopy(r)
                    part_amt = remainder if idx == split_count - 1 else base_part
                    part_dt = orig_eff + timedelta(days=idx * split_interval_days)
                    part["row_id"] = f"{r['row_id']}-S{idx + 1}"
                    part["amount"] = part_amt
                    part["signed_amount"] = -part_amt
                    part["effective_date"] = part_dt.isoformat()
                    part["simulated_date"] = part_dt.isoformat()
                    part["ledger_state"] = "SETTLED" if part_dt <= as_of_dt else "SCHEDULED"
                    part["is_historical"] = part_dt <= as_of_dt
                    updated_records.append(part)
            else:
                # Pure shift later
                part = copy.deepcopy(r)
                new_dt = (
                    date.fromisoformat(str(explicit_date_str))
                    if explicit_date_str
                    else orig_eff + timedelta(days=abs(shift_days))
                )
                part["effective_date"] = new_dt.isoformat()
                part["simulated_date"] = new_dt.isoformat()
                part["ledger_state"] = "SETTLED" if new_dt <= as_of_dt else "SCHEDULED"
                part["is_historical"] = new_dt <= as_of_dt
                updated_records.append(part)

        applied_log["modified_transaction_ids"] = modified_ids
        return updated_records, safety_reserve, applied_log

    applied_log["warning"] = f"Unrecognized intervention type '{raw_type}' ignored."
    return records, safety_reserve, applied_log


def run_what_if_simulation(
    normalized_records: list[dict[str, Any]],
    opening_cash: float,
    safety_reserve: float,
    as_of_date: date | str,
    interventions: list[dict[str, Any]],
    scenario_name: str = "What-If Simulation",
) -> dict[str, Any]:
    """
    Execute a non-mutating what-if simulation on a deep copy of `normalized_records`.
    Supports single or combined interventions:
    - CUSTOMER_PAYMENT_EARLIER
    - SUPPLIER_PAYMENT_SHIFTED / SUPPLIER_PAYMENT_SPLIT
    - SAFETY_RESERVE_CHANGED
    """
    as_of_dt = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date

    # 1. Compute baseline metrics (without mutating input)
    base_records = copy.deepcopy(normalized_records)
    base_recon = reconstruct_cash_timeline(
        base_records,
        opening_cash=opening_cash,
        as_of_date=as_of_dt,
        safety_reserve=safety_reserve,
    )
    base_dz = attach_root_causes_to_dead_zones(
        detect_dead_zones(base_recon["timeline"], safety_reserve=safety_reserve),
        base_records,
    )
    base_forecasts = generate_forecasts(
        base_records,
        starting_cash=base_recon["final_closing_cash"],
        as_of_date=as_of_dt,
        safety_reserve=safety_reserve,
        historical_days_count=base_recon["days_count"],
    )

    # 2. Apply interventions to a separate clone
    sim_records = copy.deepcopy(normalized_records)
    sim_safety_reserve = round(float(safety_reserve), 2)
    applied_interventions: list[dict[str, Any]] = []

    for interv in interventions:
        sim_records, sim_safety_reserve, log_item = _apply_single_intervention(
            sim_records, sim_safety_reserve, as_of_dt, interv
        )
        applied_interventions.append(log_item)

    sim_records.sort(key=lambda x: (x["effective_date"], x["row_id"]))

    # 3. Reconstruct & detect dead zones on simulated dataset
    sim_recon = reconstruct_cash_timeline(
        sim_records,
        opening_cash=opening_cash,
        as_of_date=as_of_dt,
        safety_reserve=sim_safety_reserve,
    )
    sim_dz = attach_root_causes_to_dead_zones(
        detect_dead_zones(sim_recon["timeline"], safety_reserve=sim_safety_reserve),
        sim_records,
    )
    sim_forecasts = generate_forecasts(
        sim_records,
        starting_cash=sim_recon["final_closing_cash"],
        as_of_date=as_of_dt,
        safety_reserve=sim_safety_reserve,
        historical_days_count=sim_recon["days_count"],
    )

    # 4. Compute delta comparison (historical + 30d forecast combined view)
    base_30d_dz = base_forecasts["horizons"]["30_days"]["dead_zones"]
    sim_30d_dz = sim_forecasts["horizons"]["30_days"]["dead_zones"]

    base_total_dz_count = len(base_dz) + len(base_30d_dz)
    sim_total_dz_count = len(sim_dz) + len(sim_30d_dz)

    base_min_cash = min(
        base_recon["min_closing_cash"],
        base_forecasts["horizons"]["30_days"]["min_projected_cash"],
    )
    sim_min_cash = min(
        sim_recon["min_closing_cash"],
        sim_forecasts["horizons"]["30_days"]["min_projected_cash"],
    )

    base_max_shortfall = max(
        [d["absolute_shortfall"] for d in (base_dz + base_30d_dz)] or [0.0]
    )
    sim_max_shortfall = max(
        [d["absolute_shortfall"] for d in (sim_dz + sim_30d_dz)] or [0.0]
    )

    return {
        "scenario_name": scenario_name,
        "as_of_date": as_of_dt.isoformat(),
        "applied_interventions": applied_interventions,
        "comparison": {
            "baseline_dead_zones_count": len(base_dz),
            "simulated_dead_zones_count": len(sim_dz),
            "baseline_forecast_30d_dead_zones_count": len(base_30d_dz),
            "simulated_forecast_30d_dead_zones_count": len(sim_30d_dz),
            "total_dead_zones_delta": sim_total_dz_count - base_total_dz_count,
            "dead_zones_eliminated": max(0, base_total_dz_count - sim_total_dz_count),
            "baseline_historical_min_cash": round(base_recon["min_closing_cash"], 2),
            "simulated_historical_min_cash": round(sim_recon["min_closing_cash"], 2),
            "historical_min_cash_improvement": round(
                sim_recon["min_closing_cash"] - base_recon["min_closing_cash"], 2
            ),
            "baseline_min_cash": round(base_min_cash, 2),
            "simulated_min_cash": round(sim_min_cash, 2),
            "min_cash_improvement": round(sim_min_cash - base_min_cash, 2),
            "baseline_max_shortfall": round(base_max_shortfall, 2),
            "simulated_max_shortfall": round(sim_max_shortfall, 2),
            "shortfall_reduction": round(base_max_shortfall - sim_max_shortfall, 2),
            "baseline_safety_reserve": round(float(safety_reserve), 2),
            "simulated_safety_reserve": sim_safety_reserve,
        },
        "baseline": {
            "safety_reserve": round(float(safety_reserve), 2),
            "reconstruction": base_recon,
            "dead_zones": base_dz,
            "forecasts": base_forecasts,
        },
        "simulated": {
            "safety_reserve": sim_safety_reserve,
            "reconstruction": sim_recon,
            "dead_zones": sim_dz,
            "forecasts": sim_forecasts,
        },
    }

