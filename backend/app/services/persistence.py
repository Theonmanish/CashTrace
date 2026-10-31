"""Persistence service mapping CashTrace domain objects to the fixed Supabase schema with in-memory fallback."""

from __future__ import annotations

import copy
import uuid
from typing import Any

from app.core.supabase import get_supabase_admin_client, get_supabase_client
from financial_engine import run_full_analysis
from financial_engine.dead_zone_detector import DOMAIN_TO_DB_SEVERITY

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"

# Thread-safe in-memory cache keyed by analysis_id
_ANALYSIS_STORE: dict[str, dict[str, Any]] = {}
_SCENARIO_STORE: dict[str, list[dict[str, Any]]] = {}


def _get_db_client():
    """Return Supabase admin client if available, otherwise standard client."""
    return get_supabase_admin_client() or get_supabase_client()


def persist_analysis_session(
    analysis_id: str,
    analysis_result: dict[str, Any],
    account_name: str = "MSME Operating Account",
) -> dict[str, Any]:
    """
    Save the full analysis result into the in-memory store AND best-effort
    persist to the fixed Supabase tables:
    - accounts
    - transactions
    - balance_snapshots
    - dead_zone_events
    """
    payload: dict[str, Any] = {
        "analysis_id": analysis_id,
        "account_name": account_name,
        **copy.deepcopy(analysis_result),
    }

    persistence_status = {
        "in_memory": True,
        "supabase_synced": False,
        "supabase_note": "Stored in memory (Supabase not configured or unreachable).",
    }

    client = _get_db_client()
    if client is not None:
        try:
            # 1. Upsert demo user profile first (best-effort)
            try:
                client.table("profiles").upsert(
                    {
                        "id": DEMO_USER_ID,
                        "email": "demo@cashtrace.internal",
                        "full_name": "CashTrace MSME Operator",
                        "company_name": account_name,
                        "base_currency": "INR",
                        "default_min_cash_buffer": payload["safety_reserve"],
                    }
                ).execute()
            except Exception:
                pass

            # 2. Upsert `accounts` row with id = analysis_id
            account_row = {
                "id": analysis_id,
                "user_id": DEMO_USER_ID,
                "name": account_name,
                "account_type": "checking",
                "institution_name": "MSME Operating Ledger",
                "currency": "INR",
                "current_balance": payload["opening_cash"],
                "min_safety_buffer": payload["safety_reserve"],
                "is_active": True,
                "metadata": {
                    "as_of_date": payload["as_of_date"],
                    "opening_cash": payload["opening_cash"],
                    "safety_reserve": payload["safety_reserve"],
                    "final_closing_cash": payload["summary"]["final_closing_cash"],
                },
            }
            client.table("accounts").upsert(account_row).execute()

            # Clear existing child records if re-upsert for same analysis_id
            client.table("transactions").delete().eq("account_id", analysis_id).execute()
            client.table("balance_snapshots").delete().eq("account_id", analysis_id).execute()
            client.table("dead_zone_events").delete().eq("account_id", analysis_id).execute()

            # 3. Insert normalized `transactions`
            tx_rows = []
            for tx in payload.get("normalized_transactions", []):
                tx_rows.append(
                    {
                        "user_id": DEMO_USER_ID,
                        "account_id": analysis_id,
                        "amount": tx["signed_amount"],
                        "transaction_type": tx["type"],
                        "category": tx.get("category") or "General",
                        "description": tx.get("description") or "",
                        "counterparty": tx.get("counterparty") or "",
                        "transaction_date": tx["effective_date"],
                        "status": "completed" if tx["ledger_state"] == "SETTLED" else "scheduled",
                        "is_recurring": bool(tx.get("is_recurring", False)),
                        "recurrence_rule": tx.get("recurrence_rule"),
                        "metadata": {
                            "row_id": tx["row_id"],
                            "raw_date": tx["raw_date"],
                            "due_date": tx.get("due_date"),
                            "actual_payment_date": tx.get("actual_payment_date"),
                            "effective_date": tx["effective_date"],
                            "ledger_state": tx["ledger_state"],
                            "delay_days": tx.get("delay_days", 0),
                            "is_overdue": tx.get("is_overdue", False),
                        },
                    }
                )
            if tx_rows:
                client.table("transactions").insert(tx_rows).execute()

            # 4. Insert `balance_snapshots` (historical + 30-day forecast)
            snapshot_rows = []
            for day in payload.get("timeline", []):
                snapshot_rows.append(
                    {
                        "user_id": DEMO_USER_ID,
                        "account_id": analysis_id,
                        "snapshot_date": day["date"],
                        "opening_balance": day["opening_cash"],
                        "closing_balance": day["closing_cash"],
                        "total_inflow": day["inflows"],
                        "total_outflow": day["outflows"],
                        "is_forecast": False,
                        "confidence_score": 1.0,
                    }
                )
            forecast_30d = (
                payload.get("forecasts", {})
                .get("horizons", {})
                .get("30_days", {})
                .get("timeline", [])
            )
            for fday in forecast_30d:
                snapshot_rows.append(
                    {
                        "user_id": DEMO_USER_ID,
                        "account_id": analysis_id,
                        "snapshot_date": fday["date"],
                        "opening_balance": fday["opening_cash"],
                        "closing_balance": fday["closing_cash"],
                        "total_inflow": fday["inflows"],
                        "total_outflow": fday["outflows"],
                        "is_forecast": True,
                        "confidence_score": 0.85,
                    }
                )
            if snapshot_rows:
                client.table("balance_snapshots").upsert(
                    snapshot_rows,
                    on_conflict="user_id,account_id,snapshot_date,is_forecast",
                ).execute()

            # 5. Insert `dead_zone_events` (historical + 30d forecast dead zones)
            all_dz = list(payload.get("dead_zones", [])) + list(
                payload.get("forecasts", {})
                .get("horizons", {})
                .get("30_days", {})
                .get("dead_zones", [])
            )
            dz_rows = []
            for dz in all_dz:
                db_sev = DOMAIN_TO_DB_SEVERITY.get(dz["severity"], "warning")
                # Embed exact CashTrace domain metadata alongside root_causes array
                enriched_causes = [
                    {
                        **rc,
                        "domain_severity": dz["severity"],
                        "severity_score": dz["severity_score"],
                        "shortfall_percentage": dz["shortfall_percentage"],
                        "is_forecast": dz.get("is_forecast", False),
                        "dead_zone_id": dz["dead_zone_id"],
                    }
                    for rc in dz.get("root_causes", [])
                ]
                if not enriched_causes:
                    enriched_causes = [
                        {
                            "category": "TIMING_MISMATCH",
                            "impact_amount": dz["absolute_shortfall"],
                            "summary": "Closing cash dipped below safety reserve.",
                            "domain_severity": dz["severity"],
                            "severity_score": dz["severity_score"],
                            "shortfall_percentage": dz["shortfall_percentage"],
                            "is_forecast": dz.get("is_forecast", False),
                            "dead_zone_id": dz["dead_zone_id"],
                        }
                    ]
                dz_rows.append(
                    {
                        "user_id": DEMO_USER_ID,
                        "account_id": analysis_id,
                        "title": (
                            f"{'Forecast ' if dz.get('is_forecast') else ''}Dead Zone "
                            f"{dz['dead_zone_id']} ({dz['severity']})"
                        ),
                        "severity": db_sev,
                        "status": "active",
                        "start_date": dz["start_date"],
                        "end_date": dz["end_date"],
                        "lowest_projected_balance": dz["minimum_cash"],
                        "shortfall_amount": dz["absolute_shortfall"],
                        "root_causes": enriched_causes,
                        "recommended_actions": dz.get("recommended_actions", []),
                    }
                )
            if dz_rows:
                client.table("dead_zone_events").insert(dz_rows).execute()

            persistence_status["supabase_synced"] = True
            persistence_status["supabase_note"] = "Synced to Supabase tables (accounts, transactions, balance_snapshots, dead_zone_events)."
        except Exception as exc:
            persistence_status["supabase_note"] = f"Using in-memory store (Supabase write skipped: {exc})"

    payload["persistence"] = persistence_status
    _ANALYSIS_STORE[analysis_id] = payload
    return copy.deepcopy(payload)


def get_analysis_session(analysis_id: str) -> dict[str, Any] | None:
    """
    Retrieve an analysis session by `analysis_id` from in-memory cache,
    or reconstruct it from Supabase if not in memory.
    """
    if analysis_id in _ANALYSIS_STORE:
        return copy.deepcopy(_ANALYSIS_STORE[analysis_id])

    client = _get_db_client()
    if client is None:
        return None

    try:
        acc_resp = client.table("accounts").select("*").eq("id", analysis_id).limit(1).execute()
        if not acc_resp.data:
            return None
        acc = acc_resp.data[0]
        tx_resp = client.table("transactions").select("*").eq("account_id", analysis_id).execute()
        tx_list = tx_resp.data or []
        if not tx_list:
            return None

        raw_records = []
        for idx, t in enumerate(tx_list, start=1):
            meta = t.get("metadata") or {}
            raw_records.append(
                {
                    "row_id": meta.get("row_id") or f"ROW-{idx:04d}",
                    "date": meta.get("raw_date") or str(t.get("transaction_date", ""))[:10],
                    "type": "inflow" if float(t["amount"]) >= 0 else "outflow",
                    "amount": abs(float(t["amount"])),
                    "category": t.get("category") or "General",
                    "counterparty": t.get("counterparty") or "",
                    "description": t.get("description") or "",
                    "due_date": meta.get("due_date"),
                    "actual_payment_date": meta.get("actual_payment_date"),
                    "is_recurring": bool(t.get("is_recurring", False)),
                    "recurrence_rule": t.get("recurrence_rule"),
                }
            )

        acc_meta = acc.get("metadata") or {}
        opening_cash = float(acc_meta.get("opening_cash", acc.get("current_balance", 0.0)))
        safety_reserve = float(acc_meta.get("safety_reserve", acc.get("min_safety_buffer", 100000.0)))
        as_of_date = acc_meta.get("as_of_date")

        rebuilt = run_full_analysis(
            raw_records=raw_records,
            opening_cash=opening_cash,
            safety_reserve=safety_reserve,
            as_of_date=as_of_date,
        )
        rebuilt["analysis_id"] = analysis_id
        rebuilt["account_name"] = acc.get("name") or "MSME Operating Account"
        rebuilt["persistence"] = {
            "in_memory": True,
            "supabase_synced": True,
            "supabase_note": "Restored from Supabase.",
        }
        _ANALYSIS_STORE[analysis_id] = rebuilt
        return copy.deepcopy(rebuilt)
    except Exception:
        return None


def persist_scenario_simulation(
    analysis_id: str,
    simulation_result: dict[str, Any],
) -> dict[str, Any]:
    """Persist a what-if simulation scenario to memory and the Supabase `scenarios` table."""
    scenario_id = str(uuid.uuid4())
    result_copy = copy.deepcopy(simulation_result)
    result_copy["scenario_id"] = scenario_id
    result_copy["analysis_id"] = analysis_id

    _SCENARIO_STORE.setdefault(analysis_id, []).append(result_copy)

    client = _get_db_client()
    if client is not None:
        try:
            sim_recon = result_copy["simulated"]["reconstruction"]
            comp = result_copy["comparison"]
            scenario_row = {
                "id": scenario_id,
                "user_id": DEMO_USER_ID,
                "name": result_copy.get("scenario_name") or "What-If Simulation",
                "description": f"Simulation for analysis_id={analysis_id}",
                "baseline_start_date": sim_recon["start_date"],
                "baseline_end_date": (
                    result_copy["simulated"]["forecasts"]["horizons"]["30_days"]["end_date"]
                ),
                "adjustments": result_copy.get("applied_interventions", []),
                "projected_dead_zones_count": (
                    comp["simulated_dead_zones_count"]
                    + comp["simulated_forecast_30d_dead_zones_count"]
                ),
                "projected_min_cash": None,
                "projected_min_balance": comp["simulated_min_cash"],
                "is_recommended": comp["dead_zones_eliminated"] > 0 or comp["min_cash_improvement"] > 0,
            }
            # Remove unused key before insert
            scenario_row.pop("projected_min_cash", None)
            client.table("scenarios").insert(scenario_row).execute()
        except Exception:
            pass

    return result_copy

