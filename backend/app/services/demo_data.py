"""Realistic MSME Demo Dataset for CashTrace (INR)."""

from __future__ import annotations

from typing import Any

DEMO_ANALYSIS_ID = "33333333-3333-3333-3333-333333333333"
DEMO_OPENING_CASH = 220000.0
DEMO_SAFETY_RESERVE = 100000.0


def get_msme_demo_transactions() -> list[dict[str, Any]]:
    """
    Return a deterministic MSME ledger (Shree Precision Components Pvt Ltd)
    demonstrating:
    - Hybrid ledger (settled historical movements + overdue unpaid invoice + future scheduled flows)
    - Historical dead zone (Oct 10 - Oct 15) where cash dips below ₹1,00,000 safety reserve
    - All 4 root cause categories (CUSTOMER_PAYMENT_DELAY, SUPPLIER_PAYMENT_CLUSTER,
      RECURRING_EXPENSE_SURGE, TIMING_MISMATCH)
    - Upcoming 14d/30d forecast dead zone that can be mitigated via What-If simulation
    """
    return [
        # 1. Early October inflow (Settled on time - Recurring Monthly OEM Supply Contract)
        {
            "row_id": "TXN-1001",
            "date": "2026-10-02",
            "type": "inflow",
            "amount": 95000,
            "category": "Customer Receivable",
            "counterparty": "Bharat Auto OEM Ltd",
            "description": "Monthly OEM Gear Shaft Supply Contract",
            "due_date": "2026-10-02",
            "actual_payment_date": "2026-10-02",
            "is_recurring": True,
        },
        # 2. Recurring Monthly Factory Rent (Settled Oct 5)
        {
            "row_id": "TXN-1002",
            "date": "2026-10-05",
            "type": "outflow",
            "amount": 55000,
            "category": "Factory Rent",
            "counterparty": "MIDC Industrial Estates",
            "description": "Monthly factory shed lease",
            "due_date": None,
            "actual_payment_date": "2026-10-05",
            "is_recurring": True,
        },
        # 3. Recurring Monthly Staff Payroll (Settled Oct 7)
        {
            "row_id": "TXN-1003",
            "date": "2026-10-07",
            "type": "outflow",
            "amount": 110000,
            "category": "Payroll & Wages",
            "counterparty": "Shopfloor & Admin Payroll",
            "description": "Monthly salaries and wages",
            "due_date": None,
            "actual_payment_date": "2026-10-07",
            "is_recurring": True,
        },
        # 4. Supplier Payment Cluster #1 (Settled Oct 10 -> drops cash below ₹1,00,000!)
        {
            "row_id": "TXN-1004",
            "date": "2026-10-10",
            "type": "outflow",
            "amount": 58000,
            "category": "Raw Material Supplier",
            "counterparty": "Kalyani Steel Traders",
            "description": "Alloy steel bar procurement",
            "due_date": "2026-10-10",
            "actual_payment_date": "2026-10-10",
            "is_recurring": False,
        },
        # 5. Supplier Payment Cluster #2 (Settled Oct 11 -> deepens dead zone!)
        {
            "row_id": "TXN-1005",
            "date": "2026-10-11",
            "type": "outflow",
            "amount": 32000,
            "category": "Vendor Packaging & Logistics",
            "counterparty": "SafePack Corrugation Co",
            "description": "Industrial crates & freight dispatch",
            "due_date": "2026-10-11",
            "actual_payment_date": "2026-10-11",
            "is_recurring": False,
        },
        # 6. Delayed Customer Payment (Due Oct 08, actually paid late on Oct 16 -> exits dead zone!)
        {
            "row_id": "TXN-1006",
            "date": "2026-09-25",
            "type": "inflow",
            "amount": 140000,
            "category": "Customer Receivable",
            "counterparty": "Mahindra Agri Implements",
            "description": "Invoice #INV-882 (Delayed 8 days)",
            "due_date": "2026-10-08",
            "actual_payment_date": "2026-10-16",
            "is_recurring": False,
        },
        # 7. Recurring Electricity & Utilities (Settled Oct 18)
        {
            "row_id": "TXN-1007",
            "date": "2026-10-18",
            "type": "outflow",
            "amount": 24000,
            "category": "Electricity & Utilities",
            "counterparty": "MSEDCL Power",
            "description": "Three-phase industrial power bill",
            "due_date": None,
            "actual_payment_date": "2026-10-18",
            "is_recurring": True,
        },
        # 8. Overdue Unpaid Customer Invoice (Due Oct 19, actual_payment_date EMPTY -> MUST NOT enter historical cash!)
        {
            "row_id": "TXN-1008",
            "date": "2026-10-04",
            "type": "inflow",
            "amount": 85000,
            "category": "Customer Receivable",
            "counterparty": "Apex Earthmovers Pvt Ltd",
            "description": "Invoice #INV-901 (Overdue Unpaid Receivable)",
            "due_date": "2026-10-19",
            "actual_payment_date": None,
            "is_recurring": False,
        },
        # 9. Latest settled transaction (Sets deterministic default as_of_date = 2026-10-20)
        {
            "row_id": "TXN-1009",
            "date": "2026-10-20",
            "type": "outflow",
            "amount": 16000,
            "category": "GST & Statutory",
            "counterparty": "GSTN Portal",
            "description": "Monthly GSTR-3B tax remittance",
            "due_date": "2026-10-20",
            "actual_payment_date": "2026-10-20",
            "is_recurring": True,
        },
        # 10. Scheduled Future Supplier Outflow (Due Oct 24 -> Triggers upcoming forecast dead zone)
        {
            "row_id": "TXN-1010",
            "date": "2026-10-15",
            "type": "outflow",
            "amount": 165000,
            "category": "Raw Material Supplier",
            "counterparty": "Tata Metaliks Distributor",
            "description": "Scheduled Q4 Forging Billet Lot",
            "due_date": "2026-10-24",
            "actual_payment_date": None,
            "is_recurring": False,
        },
        # 11. Scheduled Future Vendor Outflow (Due Oct 25)
        {
            "row_id": "TXN-1011",
            "date": "2026-10-18",
            "type": "outflow",
            "amount": 35000,
            "category": "Supplier Tooling",
            "counterparty": "Carbide CNC Tools India",
            "description": "Scheduled CNC inserts bill",
            "due_date": "2026-10-25",
            "actual_payment_date": None,
            "is_recurring": False,
        },
        # 12. Scheduled Future Customer Receivable (Due Nov 02)
        {
            "row_id": "TXN-1012",
            "date": "2026-10-19",
            "type": "inflow",
            "amount": 180000,
            "category": "Customer Receivable",
            "counterparty": "Kirloskar Fluid Systems",
            "description": "Scheduled Invoice #INV-915 settlement",
            "due_date": "2026-11-02",
            "actual_payment_date": None,
            "is_recurring": False,
        },
    ]

