"""Normalization and Hybrid Ledger classification for CashTrace."""

from __future__ import annotations

from datetime import date
from typing import Any

from financial_engine.validator import INFLOW_ALIASES, parse_date_value, validate_records


def normalize_type(type_token: str) -> str:
    """Normalize transaction type alias into 'inflow' or 'outflow'."""
    token = type_token.strip().lower()
    if token in INFLOW_ALIASES:
        return "inflow"
    return "outflow"


def normalize_records(
    raw_or_validated_records: list[dict[str, Any]],
    as_of_date: date | str | None = None,
) -> tuple[list[dict[str, Any]], date]:
    """
    Normalize validated records according to CashTrace Hybrid Ledger rules:

    1. Positive internal amounts (`amount > 0`), `type` in `{'inflow', 'outflow'}`.
    2. Hybrid Ledger classification:
       - If `due_date` is absent:
           ledger_state = 'SETTLED'
           effective_date = actual_payment_date if present else date
       - If `due_date` exists AND `actual_payment_date` exists:
           ledger_state = 'SETTLED'
           effective_date = actual_payment_date
       - If `due_date` exists AND `actual_payment_date` is empty:
           ledger_state = 'SCHEDULED'
           effective_date = due_date
           (Does NOT affect historical cash, even if overdue!)
    3. `as_of_date` defaults deterministically to the latest SETTLED `effective_date`
       (or latest row `date` if no settled transactions exist).
    """
    # Check if already validated by looking for `type_token` and `raw_amount`
    if raw_or_validated_records and "type_token" in raw_or_validated_records[0]:
        validated = raw_or_validated_records
    else:
        validated = validate_records(raw_or_validated_records)

    normalized: list[dict[str, Any]] = []

    for item in validated:
        tx_date: date = item["date"]
        due_date: date | None = item.get("due_date")
        actual_payment_date: date | None = item.get("actual_payment_date")

        tx_type = normalize_type(item["type_token"])
        positive_amount = round(abs(float(item["raw_amount"])), 2)

        if due_date is None:
            ledger_state = "SETTLED"
            effective_date = actual_payment_date if actual_payment_date is not None else tx_date
            delay_days = (
                (actual_payment_date - tx_date).days
                if actual_payment_date is not None and actual_payment_date > tx_date
                else 0
            )
        elif actual_payment_date is not None:
            ledger_state = "SETTLED"
            effective_date = actual_payment_date
            delay_days = max(0, (actual_payment_date - due_date).days)
        else:
            ledger_state = "SCHEDULED"
            effective_date = due_date
            delay_days = 0

        category = item.get("category") or ("Receivable" if tx_type == "inflow" else "Operating Expense")

        normalized.append(
            {
                "row_id": item["row_id"],
                "raw_date": item["raw_date"],
                "date": tx_date.isoformat(),
                "due_date": due_date.isoformat() if due_date else None,
                "actual_payment_date": actual_payment_date.isoformat() if actual_payment_date else None,
                "effective_date": effective_date.isoformat(),
                "type": tx_type,
                "amount": positive_amount,
                "signed_amount": positive_amount if tx_type == "inflow" else -positive_amount,
                "category": category,
                "counterparty": item.get("counterparty") or "",
                "description": item.get("description") or "",
                "ledger_state": ledger_state,
                "delay_days": delay_days,
                "is_recurring": bool(item.get("is_recurring", False)),
                "recurrence_rule": item.get("recurrence_rule"),
            }
        )

    parsed_as_of = parse_date_value(as_of_date, "as_of_date") if as_of_date else None
    if parsed_as_of is None:
        settled_dates = [
            date.fromisoformat(r["effective_date"])
            for r in normalized
            if r["ledger_state"] == "SETTLED"
        ]
        if settled_dates:
            parsed_as_of = max(settled_dates)
        else:
            all_dates = [date.fromisoformat(r["date"]) for r in normalized]
            parsed_as_of = max(all_dates) if all_dates else date.today()

    # Annotate overdue status relative to deterministic `as_of_date`
    for r in normalized:
        eff_dt = date.fromisoformat(r["effective_date"])
        if r["ledger_state"] == "SCHEDULED" and r["due_date"]:
            due_dt = date.fromisoformat(r["due_date"])
            r["is_overdue"] = due_dt <= parsed_as_of
            if due_dt <= parsed_as_of:
                r["delay_days"] = (parsed_as_of - due_dt).days
        else:
            r["is_overdue"] = False
        # If an explicitly supplied `as_of_date` is earlier than a settled row's effective_date,
        # treat it as scheduled relative to `as_of_date`
        r["is_historical"] = r["ledger_state"] == "SETTLED" and eff_dt <= parsed_as_of

    # Sort deterministically by effective_date, then row_id
    normalized.sort(key=lambda x: (x["effective_date"], x["row_id"]))
    return normalized, parsed_as_of

