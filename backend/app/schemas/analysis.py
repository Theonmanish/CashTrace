"""Pydantic request and response schemas for CashTrace API."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class TransactionInput(BaseModel):
    """Single transaction record in JSON input."""

    id: Optional[str] = None
    row_id: Optional[str] = None
    transaction_id: Optional[str] = None
    date: str
    type: str
    amount: float | str
    category: Optional[str] = "General"
    counterparty: Optional[str] = ""
    party: Optional[str] = None
    description: Optional[str] = ""
    due_date: Optional[str] = None
    actual_payment_date: Optional[str] = None
    is_recurring: Optional[bool] = False
    recurrence_rule: Optional[str] = None


class AnalyzeJsonRequest(BaseModel):
    """JSON payload for POST /api/analyze."""

    opening_cash: float = Field(..., description="Starting cash balance in INR")
    safety_reserve: float = Field(
        default=100000.0,
        description="Minimum safety cash reserve in INR (default ₹1,00,000)",
    )
    as_of_date: Optional[str] = Field(
        default=None,
        description="Optional deterministic cutoff date (YYYY-MM-DD). Defaults to latest settled effective date.",
    )
    analysis_id: Optional[str] = Field(
        default=None,
        description="Optional UUID for the analysis session.",
    )
    account_name: Optional[str] = Field(
        default="MSME Operating Account",
        description="Display name for the analyzed account.",
    )
    transactions: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="List of raw transaction objects.",
    )
    csv_content: Optional[str] = Field(
        default=None,
        description="Raw CSV string if submitting CSV inside JSON.",
    )


class SplitInstallment(BaseModel):
    """Installment specification when splitting a supplier payment."""

    date: Optional[str] = None
    amount: float


class InterventionInput(BaseModel):
    """Single What-If intervention specification."""

    type: str = Field(
        ...,
        description=(
            "Intervention type: CUSTOMER_PAYMENT_EARLIER | "
            "SUPPLIER_PAYMENT_SHIFTED | SUPPLIER_PAYMENT_SPLIT | SAFETY_RESERVE_CHANGED"
        ),
    )
    transaction_id: Optional[str] = Field(
        default=None,
        description="Target row_id / transaction_id to modify.",
    )
    transaction_ids: Optional[list[str]] = Field(
        default=None,
        description="Optional list of target row_ids.",
    )
    days_earlier: Optional[int] = Field(
        default=None,
        description="Days to pull a customer payment earlier.",
    )
    shift_days: Optional[int] = Field(
        default=None,
        description="Days to defer/shift a supplier payment later.",
    )
    new_date: Optional[str] = Field(
        default=None,
        description="Explicit new effective date (YYYY-MM-DD) for the transaction.",
    )
    split_count: Optional[int] = Field(
        default=None,
        description="Number of equal installments to split a supplier outflow into.",
    )
    split_interval_days: Optional[int] = Field(
        default=None,
        description="Days between split installments.",
    )
    splits: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Explicit list of installments [{'date': 'YYYY-MM-DD', 'amount': 50000}].",
    )
    new_safety_reserve: Optional[float] = Field(
        default=None,
        description="Updated safety reserve in INR for SAFETY_RESERVE_CHANGED.",
    )


class SimulateRequest(BaseModel):
    """Payload for POST /api/simulate and POST /api/analysis/{analysis_id}/simulate."""

    analysis_id: Optional[str] = Field(
        default=None,
        description="ID of the existing analysis session to simulate against.",
    )
    scenario_name: str = Field(
        default="What-If Mitigation Scenario",
        description="Human-readable name for the scenario.",
    )
    interventions: list[InterventionInput] = Field(
        default_factory=list,
        description="List of one or more what-if interventions to apply.",
    )

