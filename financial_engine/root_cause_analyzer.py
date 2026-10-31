"""Evidence-backed Root Cause Analysis for CashTrace Dead Zones."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

ROOT_CAUSE_CATEGORIES = (
    "CUSTOMER_PAYMENT_DELAY",
    "SUPPLIER_PAYMENT_CLUSTER",
    "RECURRING_EXPENSE_SURGE",
    "TIMING_MISMATCH",
)

RECURRING_KEYWORDS = {
    "rent",
    "payroll",
    "salary",
    "salaries",
    "wages",
    "emi",
    "loan",
    "utility",
    "utilities",
    "electricity",
    "internet",
    "subscription",
    "insurance",
    "gst",
    "tax",
    "retainer",
}

SUPPLIER_KEYWORDS = {
    "supplier",
    "vendor",
    "inventory",
    "raw material",
    "procurement",
    "purchase",
    "freight",
    "logistics",
    "manufacturing",
    "packaging",
    "wholesaler",
}


def _is_recurring_row(row: dict[str, Any]) -> bool:
    if row.get("is_recurring"):
        return True
    text = f"{row.get('category', '')} {row.get('description', '')}".lower()
    return any(kw in text for kw in RECURRING_KEYWORDS)


def _is_supplier_row(row: dict[str, Any]) -> bool:
    text = f"{row.get('category', '')} {row.get('description', '')} {row.get('counterparty', '')}".lower()
    if any(kw in text for kw in SUPPLIER_KEYWORDS):
        return True
    return not _is_recurring_row(row)


def analyze_dead_zone_root_causes(
    dead_zone: dict[str, Any],
    normalized_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Identify evidence-backed root causes for a single dead zone using ONLY:
    - CUSTOMER_PAYMENT_DELAY
    - SUPPLIER_PAYMENT_CLUSTER
    - RECURRING_EXPENSE_SURGE
    - TIMING_MISMATCH

    Never claims a root cause without supporting transaction evidence.
    Returns (root_causes, recommended_actions).
    """
    dz_start = date.fromisoformat(dead_zone["start_date"])
    dz_end = date.fromisoformat(dead_zone["end_date"])
    lookback_start = dz_start - timedelta(days=7)
    lookahead_end = dz_end + timedelta(days=10)

    causes: list[dict[str, Any]] = []
    recommendations: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 1. CUSTOMER_PAYMENT_DELAY
    # Evidence:
    #   (a) Inflow rows with `due_date` in [lookback_start .. dz_end] that are still
    #       unpaid (`SCHEDULED`), OR
    #   (b) Inflow rows with `due_date` in [lookback_start .. dz_end] that were settled
    #       late (`actual_payment_date > due_date` and after `dz_start`).
    # ------------------------------------------------------------------
    delayed_inflows: list[dict[str, Any]] = []
    for r in normalized_records:
        if r["type"] != "inflow" or not r.get("due_date"):
            continue
        due_dt = date.fromisoformat(r["due_date"])
        if not (lookback_start - timedelta(days=14) <= due_dt <= dz_end):
            continue

        if r["ledger_state"] == "SCHEDULED":
            delayed_inflows.append(r)
        elif r.get("actual_payment_date"):
            paid_dt = date.fromisoformat(r["actual_payment_date"])
            if paid_dt > due_dt and paid_dt > dz_start:
                delayed_inflows.append(r)

    if delayed_inflows:
        impact = round(sum(float(r["amount"]) for r in delayed_inflows), 2)
        evidence_ids = [r["row_id"] for r in delayed_inflows]
        evidence_items = [
            {
                "row_id": r["row_id"],
                "counterparty": r.get("counterparty") or "Customer",
                "amount": r["amount"],
                "due_date": r["due_date"],
                "actual_payment_date": r.get("actual_payment_date"),
                "ledger_state": r["ledger_state"],
                "delay_days": r.get("delay_days", 0),
            }
            for r in delayed_inflows
        ]
        parties = ", ".join(
            sorted({r.get("counterparty") or r["row_id"] for r in delayed_inflows})[:3]
        )
        causes.append(
            {
                "category": "CUSTOMER_PAYMENT_DELAY",
                "impact_amount": impact,
                "summary": (
                    f"{len(delayed_inflows)} customer receivable(s) totaling ₹{impact:,.2f} "
                    f"({parties}) were due on or before {dz_end.isoformat()} but delayed or unpaid."
                ),
                "evidence_transaction_ids": evidence_ids,
                "evidence": evidence_items,
            }
        )
        recommendations.append(
            {
                "action_type": "CUSTOMER_PAYMENT_EARLIER",
                "title": f"Accelerate collection of ₹{impact:,.2f} from {parties}",
                "expected_impact": impact,
                "target_transaction_ids": evidence_ids,
            }
        )

    # ------------------------------------------------------------------
    # 2. SUPPLIER_PAYMENT_CLUSTER
    # Evidence:
    #   2+ supplier/vendor outflows (or a single large supplier outflow >= 40% of safety reserve)
    #   falling within [dz_start - 3 days .. dz_end].
    # ------------------------------------------------------------------
    cluster_window_start = dz_start - timedelta(days=3)
    window_outflows = [
        r
        for r in normalized_records
        if r["type"] == "outflow"
        and cluster_window_start <= date.fromisoformat(r["effective_date"]) <= dz_end
    ]
    supplier_outflows = [r for r in window_outflows if _is_supplier_row(r)]

    safety_res = max(float(dead_zone.get("safety_reserve", 100000.0)), 1.0)
    supplier_total = round(sum(float(r["amount"]) for r in supplier_outflows), 2)

    if len(supplier_outflows) >= 2 or (
        len(supplier_outflows) == 1 and supplier_total >= 0.4 * safety_res
    ):
        evidence_ids = [r["row_id"] for r in supplier_outflows]
        evidence_items = [
            {
                "row_id": r["row_id"],
                "counterparty": r.get("counterparty") or r.get("category") or "Supplier",
                "amount": r["amount"],
                "effective_date": r["effective_date"],
                "category": r.get("category"),
            }
            for r in supplier_outflows
        ]
        vendors = ", ".join(
            sorted({r.get("counterparty") or r.get("category") or r["row_id"] for r in supplier_outflows})[:3]
        )
        causes.append(
            {
                "category": "SUPPLIER_PAYMENT_CLUSTER",
                "impact_amount": supplier_total,
                "summary": (
                    f"{len(supplier_outflows)} supplier/procurement outflow(s) totaling ₹{supplier_total:,.2f} "
                    f"({vendors}) clustered between {cluster_window_start.isoformat()} and {dz_end.isoformat()}."
                ),
                "evidence_transaction_ids": evidence_ids,
                "evidence": evidence_items,
            }
        )
        largest_supplier = max(supplier_outflows, key=lambda x: float(x["amount"]))
        recommendations.append(
            {
                "action_type": "SUPPLIER_PAYMENT_SHIFTED",
                "title": (
                    f"Defer or split supplier payout {largest_supplier['row_id']} "
                    f"(₹{largest_supplier['amount']:,.2f}) by 7–10 days"
                ),
                "expected_impact": float(largest_supplier["amount"]),
                "target_transaction_ids": [largest_supplier["row_id"]],
            }
        )

    # ------------------------------------------------------------------
    # 3. RECURRING_EXPENSE_SURGE
    # Evidence:
    #   Recurring/fixed operating outflows (payroll, rent, EMI, utilities, GST)
    #   occurring inside [dz_start - 3 days .. dz_end].
    # ------------------------------------------------------------------
    recurring_outflows = [r for r in window_outflows if _is_recurring_row(r)]
    recurring_total = round(sum(float(r["amount"]) for r in recurring_outflows), 2)

    if recurring_outflows:
        evidence_ids = [r["row_id"] for r in recurring_outflows]
        evidence_items = [
            {
                "row_id": r["row_id"],
                "category": r.get("category"),
                "description": r.get("description"),
                "amount": r["amount"],
                "effective_date": r["effective_date"],
            }
            for r in recurring_outflows
        ]
        cats = ", ".join(sorted({r.get("category") or "Fixed Expense" for r in recurring_outflows}))
        causes.append(
            {
                "category": "RECURRING_EXPENSE_SURGE",
                "impact_amount": recurring_total,
                "summary": (
                    f"Fixed/recurring operating commitment(s) ({cats}) of ₹{recurring_total:,.2f} "
                    f"drained cash reserves entering the dead zone."
                ),
                "evidence_transaction_ids": evidence_ids,
                "evidence": evidence_items,
            }
        )

    # ------------------------------------------------------------------
    # 4. TIMING_MISMATCH
    # Evidence:
    #   Outflows occur before/during the dead zone while inflows arrive shortly after
    #   `dz_start` (up to `lookahead_end`), creating a temporary liquidity gap.
    # ------------------------------------------------------------------
    post_inflows = [
        r
        for r in normalized_records
        if r["type"] == "inflow"
        and dz_start < date.fromisoformat(r["effective_date"]) <= lookahead_end
    ]
    if window_outflows and post_inflows:
        out_sum = round(sum(float(r["amount"]) for r in window_outflows), 2)
        in_sum = round(sum(float(r["amount"]) for r in post_inflows), 2)
        evidence_ids = [r["row_id"] for r in window_outflows[:3] + post_inflows[:3]]
        causes.append(
            {
                "category": "TIMING_MISMATCH",
                "impact_amount": min(out_sum, in_sum),
                "summary": (
                    f"Outflows of ₹{out_sum:,.2f} hit between {cluster_window_start.isoformat()} and "
                    f"{dz_end.isoformat()}, whereas ₹{in_sum:,.2f} in inflows arrive later "
                    f"(by {lookahead_end.isoformat()})."
                ),
                "evidence_transaction_ids": evidence_ids,
                "evidence": [
                    {
                        "row_id": r["row_id"],
                        "type": r["type"],
                        "amount": r["amount"],
                        "effective_date": r["effective_date"],
                        "counterparty": r.get("counterparty") or r.get("category"),
                    }
                    for r in (window_outflows[:3] + post_inflows[:3])
                ],
            }
        )
        if not recommendations and post_inflows:
            first_in = post_inflows[0]
            recommendations.append(
                {
                    "action_type": "CUSTOMER_PAYMENT_EARLIER",
                    "title": (
                        f"Pull forward inflow {first_in['row_id']} (₹{first_in['amount']:,.2f}) "
                        f"to {dz_start.isoformat()} to close the timing gap"
                    ),
                    "expected_impact": float(first_in["amount"]),
                    "target_transaction_ids": [first_in["row_id"]],
                }
            )

    # Sort causes by highest impact_amount first
    causes.sort(key=lambda c: float(c.get("impact_amount", 0.0)), reverse=True)
    return causes, recommendations


def attach_root_causes_to_dead_zones(
    dead_zones: list[dict[str, Any]],
    normalized_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrich each detected dead zone with `root_causes` and `recommended_actions`."""
    enriched: list[dict[str, Any]] = []
    for dz in dead_zones:
        causes, recs = analyze_dead_zone_root_causes(dz, normalized_records)
        dz_copy = dict(dz)
        dz_copy["root_causes"] = causes
        dz_copy["recommended_actions"] = recs
        enriched.append(dz_copy)
    return enriched

