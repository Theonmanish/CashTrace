"""CSV and JSON input validation for the CashTrace Financial Engine."""

from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from typing import Any

INFLOW_ALIASES = {
    "inflow",
    "inflows",
    "credit",
    "cr",
    "receipt",
    "receipts",
    "income",
    "revenue",
    "sale",
    "sales",
    "deposit",
    "receivable",
    "collection",
    "customer_payment",
    "in",
}

OUTFLOW_ALIASES = {
    "outflow",
    "outflows",
    "debit",
    "dr",
    "payment",
    "payments",
    "expense",
    "expenses",
    "purchase",
    "purchases",
    "withdrawal",
    "payable",
    "payout",
    "supplier_payment",
    "vendor_payment",
    "payroll",
    "out",
}

HEADER_ALIASES = {
    "id": "row_id",
    "row_id": "row_id",
    "transaction_id": "row_id",
    "txn_id": "row_id",
    "date": "date",
    "transaction_date": "date",
    "txn_date": "date",
    "invoice_date": "date",
    "type": "type",
    "transaction_type": "type",
    "txn_type": "type",
    "flow_type": "type",
    "direction": "type",
    "amount": "amount",
    "value": "amount",
    "total": "amount",
    "category": "category",
    "head": "category",
    "expense_category": "category",
    "counterparty": "counterparty",
    "party": "counterparty",
    "party_name": "counterparty",
    "vendor": "counterparty",
    "customer": "counterparty",
    "client": "counterparty",
    "supplier": "counterparty",
    "description": "description",
    "narration": "description",
    "notes": "description",
    "remarks": "description",
    "memo": "description",
    "due_date": "due_date",
    "duedate": "due_date",
    "expected_date": "due_date",
    "scheduled_date": "due_date",
    "actual_payment_date": "actual_payment_date",
    "payment_date": "actual_payment_date",
    "settled_date": "actual_payment_date",
    "settlement_date": "actual_payment_date",
    "paid_date": "actual_payment_date",
    "is_recurring": "is_recurring",
    "recurring": "is_recurring",
    "recurrence_rule": "recurrence_rule",
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
)


class ValidationError(ValueError):
    """Raised when input financial data fails validation."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or []


def parse_date_value(val: Any, field_name: str = "date") -> date | None:
    """Parse a date value from string, date, or datetime. Returns None if empty."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val

    text = str(val).strip()
    if not text or text.lower() in {"none", "null", "na", "n/a", "-", ""}:
        return None

    # Handle ISO format with timezone or fractional seconds
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Invalid date format for '{field_name}': '{text}'")


def parse_amount_value(val: Any) -> float:
    """Parse numeric amount, stripping currency symbols (₹, $, etc.) and commas."""
    if val is None:
        raise ValueError("Missing required field 'amount'")
    if isinstance(val, (int, float)):
        num = float(val)
    else:
        text = str(val).strip()
        if not text:
            raise ValueError("Empty value for 'amount'")
        # Remove currency symbols, spaces, and Indian/Western commas
        cleaned = re.sub(r"[₹$€£,\s]", "", text)
        # Handle accounting parentheses e.g. (5000) -> -5000
        if cleaned.startswith("(") and cleaned.endswith(")"):
            cleaned = "-" + cleaned[1:-1]
        try:
            num = float(cleaned)
        except ValueError as exc:
            raise ValueError(f"Invalid numeric amount: '{text}'") from exc

    if num == 0:
        raise ValueError("Transaction amount cannot be zero")
    return num


def parse_bool_value(val: Any) -> bool:
    """Parse boolean flag from string or bool."""
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    text = str(val).strip().lower()
    return text in {"true", "1", "yes", "y", "recurring", "monthly", "weekly"}


def canonicalize_row_keys(raw_row: dict[str, Any]) -> dict[str, Any]:
    """Map raw CSV/JSON column headers to canonical CashTrace field names."""
    canonical: dict[str, Any] = {}
    for k, v in raw_row.items():
        if k is None:
            continue
        clean_key = re.sub(r"[^a-z0-9_]", "_", str(k).strip().lower()).strip("_")
        mapped_key = HEADER_ALIASES.get(clean_key, clean_key)
        # Do not overwrite an already-populated canonical field with an empty alias
        if mapped_key not in canonical or (canonical[mapped_key] in (None, "") and v not in (None, "")):
            canonical[mapped_key] = v
    return canonical


def parse_csv_content(csv_content: str | bytes) -> list[dict[str, Any]]:
    """Parse CSV text or bytes into a list of raw row dictionaries."""
    if isinstance(csv_content, bytes):
        text = csv_content.decode("utf-8-sig", errors="replace")
    else:
        text = csv_content.lstrip("\ufeff")

    text = text.strip()
    if not text:
        raise ValidationError("Uploaded CSV content is empty.")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValidationError("CSV header row is missing.")

    rows = [dict(r) for r in reader if any(v is not None and str(v).strip() != "" for v in r.values())]
    if not rows:
        raise ValidationError("CSV contains no data rows.")
    return rows


def validate_records(raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Validate a list of raw transaction dicts.

    Required fields:
    - date
    - type
    - amount

    Returns canonicalized, validated dictionaries ready for normalization.
    Raises ValidationError if any row has invalid required fields.
    """
    if not raw_records:
        raise ValidationError("No transaction records provided for analysis.")

    validated: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for idx, raw_row in enumerate(raw_records, start=1):
        row = canonicalize_row_keys(raw_row)
        row_id = str(row.get("row_id") or f"ROW-{idx:04d}").strip()
        row_errors: list[str] = []

        # 1. Validate required `date`
        raw_date = row.get("date")
        parsed_date: date | None = None
        if raw_date is None or str(raw_date).strip() == "":
            row_errors.append("Missing required field 'date'")
        else:
            try:
                parsed_date = parse_date_value(raw_date, "date")
                if parsed_date is None:
                    row_errors.append("Missing required field 'date'")
            except ValueError as exc:
                row_errors.append(str(exc))

        # 2. Validate required `type`
        raw_type = row.get("type")
        clean_type = str(raw_type or "").strip().lower()
        clean_type_token = re.sub(r"[^a-z_]", "_", clean_type).strip("_")
        if not clean_type_token:
            row_errors.append("Missing required field 'type'")
        elif clean_type_token not in INFLOW_ALIASES and clean_type_token not in OUTFLOW_ALIASES:
            row_errors.append(
                f"Unsupported transaction type '{raw_type}'. Use 'inflow' or 'outflow' (or credit/debit/receipt/payment)."
            )

        # 3. Validate required `amount`
        raw_amount = row.get("amount")
        parsed_amount: float | None = None
        try:
            parsed_amount = parse_amount_value(raw_amount)
        except ValueError as exc:
            row_errors.append(str(exc))

        # 4. Validate optional `due_date` and `actual_payment_date`
        parsed_due_date: date | None = None
        if row.get("due_date") not in (None, ""):
            try:
                parsed_due_date = parse_date_value(row.get("due_date"), "due_date")
            except ValueError as exc:
                row_errors.append(str(exc))

        parsed_actual_payment_date: date | None = None
        if row.get("actual_payment_date") not in (None, ""):
            try:
                parsed_actual_payment_date = parse_date_value(
                    row.get("actual_payment_date"), "actual_payment_date"
                )
            except ValueError as exc:
                row_errors.append(str(exc))

        if row_errors:
            errors.append(
                {
                    "row_index": idx,
                    "row_id": row_id,
                    "errors": row_errors,
                }
            )
            continue

        validated.append(
            {
                "row_id": row_id,
                "raw_date": str(raw_date).strip(),
                "date": parsed_date,
                "raw_type": str(raw_type).strip(),
                "type_token": clean_type_token,
                "raw_amount": parsed_amount,
                "category": str(row.get("category") or "General").strip() or "General",
                "counterparty": str(row.get("counterparty") or "").strip(),
                "description": str(row.get("description") or "").strip(),
                "due_date": parsed_due_date,
                "actual_payment_date": parsed_actual_payment_date,
                "is_recurring": parse_bool_value(row.get("is_recurring")),
                "recurrence_rule": str(row.get("recurrence_rule") or "").strip() or None,
            }
        )

    if errors:
        raise ValidationError(
            f"Validation failed for {len(errors)} row(s).",
            errors=errors,
        )

    return validated

