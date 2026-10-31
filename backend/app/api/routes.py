"""FastAPI routes for the CashTrace Financial Dead Zone Detector."""

from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse

from app.schemas.analysis import SimulateRequest
from app.services.demo_data import (
    DEMO_ANALYSIS_ID,
    DEMO_OPENING_CASH,
    DEMO_SAFETY_RESERVE,
    get_msme_demo_transactions,
)
from app.services.persistence import (
    get_analysis_session,
    persist_analysis_session,
    persist_scenario_simulation,
)
from financial_engine import (
    DEFAULT_SAFETY_RESERVE,
    ValidationError,
    parse_csv_content,
    run_full_analysis,
    run_what_if_simulation,
)

router = APIRouter(prefix="/api", tags=["CashTrace Analysis"])


def _ensure_uuid(candidate: str | None) -> str:
    """Ensure analysis_id is a valid UUID string (required by accounts.id UUID column)."""
    if not candidate:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(str(candidate)))
    except ValueError:
        # Deterministically derive a UUID5 if the caller passed a custom string ID
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"cashtrace.{candidate}"))


def _build_or_get_demo_analysis() -> dict[str, Any]:
    """Ensure the MSME demo analysis is initialized and return it."""
    existing = get_analysis_session(DEMO_ANALYSIS_ID)
    if existing is not None:
        return existing

    demo_rows = get_msme_demo_transactions()
    result = run_full_analysis(
        raw_records=demo_rows,
        opening_cash=DEMO_OPENING_CASH,
        safety_reserve=DEMO_SAFETY_RESERVE,
        as_of_date=None,
    )
    persisted = persist_analysis_session(
        analysis_id=DEMO_ANALYSIS_ID,
        analysis_result=result,
        account_name="Shree Precision Components Pvt Ltd (Demo MSME)",
    )
    return persisted


@router.get("/demo")
def get_demo_analysis() -> dict[str, Any]:
    """Load and return the pre-built MSME demo analysis immediately."""
    return _build_or_get_demo_analysis()


@router.post("/demo/analyze")
def post_demo_analysis() -> dict[str, Any]:
    """Re-run and return the pre-built MSME demo analysis."""
    demo_rows = get_msme_demo_transactions()
    result = run_full_analysis(
        raw_records=demo_rows,
        opening_cash=DEMO_OPENING_CASH,
        safety_reserve=DEMO_SAFETY_RESERVE,
        as_of_date=None,
    )
    persisted = persist_analysis_session(
        analysis_id=DEMO_ANALYSIS_ID,
        analysis_result=result,
        account_name="Shree Precision Components Pvt Ltd (Demo MSME)",
    )
    return {
        "analysis_id": persisted["analysis_id"],
        **persisted,
    }


@router.get("/demo/sample-csv", response_class=PlainTextResponse)
def get_sample_csv() -> str:
    """Return a ready-to-upload sample MSME CSV file."""
    rows = get_msme_demo_transactions()
    headers = [
        "row_id",
        "date",
        "type",
        "amount",
        "category",
        "counterparty",
        "description",
        "due_date",
        "actual_payment_date",
        "is_recurring",
    ]
    lines = [",".join(headers)]
    for r in rows:
        vals = [
            str(r.get(h) if r.get(h) is not None else "")
            for h in headers
        ]
        lines.append(",".join(vals))
    return "\n".join(lines)


@router.post("/analyze")
async def analyze_financial_data(request: Request) -> dict[str, Any]:
    """
    Unified endpoint accepting EITHER:
    1) `multipart/form-data` with:
       - `file`: CSV file upload (or `csv_content` text field)
       - `opening_cash`: float (required, defaults to 0.0 if omitted in form)
       - `safety_reserve`: float (optional, default 100000.0)
       - `as_of_date`: optional YYYY-MM-DD
       - `analysis_id`: optional UUID
    2) `application/json` with:
       - `transactions`: list of transaction dicts (or `csv_content`: raw CSV string)
       - `opening_cash`: float
       - `safety_reserve`: float (default 100000.0)
       - `as_of_date`: optional YYYY-MM-DD
       - `analysis_id`: optional UUID
    """
    content_type = (request.headers.get("content-type") or "").lower()

    raw_records: list[dict[str, Any]] = []
    opening_cash: float = 0.0
    safety_reserve: float = DEFAULT_SAFETY_RESERVE
    as_of_date: Optional[str] = None
    analysis_id_raw: Optional[str] = None
    account_name: str = "MSME Operating Account"

    try:
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            form = await request.form()

            if form.get("opening_cash") is None or str(form.get("opening_cash")).strip() == "":
                raise HTTPException(
                    status_code=422,
                    detail="Field 'opening_cash' is required.",
                )
            try:
                opening_cash = float(str(form.get("opening_cash")).replace(",", "").replace("₹", "").strip())
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid 'opening_cash': {exc}") from exc

            if form.get("safety_reserve") not in (None, ""):
                try:
                    safety_reserve = float(
                        str(form.get("safety_reserve")).replace(",", "").replace("₹", "").strip()
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=f"Invalid 'safety_reserve': {exc}") from exc

            if form.get("as_of_date") not in (None, ""):
                as_of_date = str(form.get("as_of_date")).strip()

            if form.get("analysis_id") not in (None, ""):
                analysis_id_raw = str(form.get("analysis_id")).strip()

            if form.get("account_name") not in (None, ""):
                account_name = str(form.get("account_name")).strip()

            upload = form.get("file") or form.get("csv_file")
            if upload is not None and hasattr(upload, "read"):
                file_bytes = await upload.read()  # type: ignore[union-attr]
                raw_records = parse_csv_content(file_bytes)
            elif form.get("csv_content") not in (None, ""):
                raw_records = parse_csv_content(str(form.get("csv_content")))
            elif form.get("transactions") not in (None, ""):
                raw_records = json.loads(str(form.get("transactions")))
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Provide a CSV 'file' upload, 'csv_content', or 'transactions' JSON in form data.",
                )
        else:
            body = await request.json()
            if not isinstance(body, dict):
                raise HTTPException(status_code=422, detail="JSON request body must be an object.")

            if "opening_cash" not in body or body["opening_cash"] is None:
                raise HTTPException(status_code=422, detail="Field 'opening_cash' is required.")

            opening_cash = float(body["opening_cash"])
            if body.get("safety_reserve") is not None:
                safety_reserve = float(body["safety_reserve"])
            as_of_date = body.get("as_of_date") or None
            analysis_id_raw = body.get("analysis_id") or None
            account_name = body.get("account_name") or "MSME Operating Account"

            if body.get("transactions") is not None:
                if not isinstance(body["transactions"], list):
                    raise HTTPException(status_code=422, detail="'transactions' must be a JSON array.")
                raw_records = body["transactions"]
            elif body.get("csv_content"):
                raw_records = parse_csv_content(str(body["csv_content"]))
            else:
                raise HTTPException(
                    status_code=422,
                    detail="Provide either 'transactions' (array) or 'csv_content' (CSV string) in JSON body.",
                )

        analysis_result = run_full_analysis(
            raw_records=raw_records,
            opening_cash=opening_cash,
            safety_reserve=safety_reserve,
            as_of_date=as_of_date,
        )
        resolved_analysis_id = _ensure_uuid(analysis_id_raw)
        persisted = persist_analysis_session(
            analysis_id=resolved_analysis_id,
            analysis_result=analysis_result,
            account_name=account_name,
        )
        return persisted

    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": exc.message,
                "errors": exc.errors,
            },
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": f"Analysis failed: {exc}"},
        ) from exc


@router.get("/analysis/{analysis_id}")
def get_analysis_by_id(analysis_id: str) -> dict[str, Any]:
    """Retrieve a stored analysis session by `analysis_id`."""
    if analysis_id.lower() == "demo" or analysis_id == DEMO_ANALYSIS_ID:
        return _build_or_get_demo_analysis()

    resolved_id = _ensure_uuid(analysis_id)
    session = get_analysis_session(resolved_id) or get_analysis_session(analysis_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail=f"Analysis session '{analysis_id}' not found.",
        )
    return session


@router.get("/analysis/{analysis_id}/dead-zones")
def get_analysis_dead_zones(analysis_id: str) -> dict[str, Any]:
    """Return historical and forecasted dead zones and root causes for an analysis."""
    session = get_analysis_by_id(analysis_id)
    return {
        "analysis_id": session["analysis_id"],
        "as_of_date": session["as_of_date"],
        "safety_reserve": session["safety_reserve"],
        "historical_dead_zones": session["dead_zones"],
        "forecast_7d_dead_zones": session["forecasts"]["horizons"]["7_days"]["dead_zones"],
        "forecast_14d_dead_zones": session["forecasts"]["horizons"]["14_days"]["dead_zones"],
        "forecast_30d_dead_zones": session["forecasts"]["horizons"]["30_days"]["dead_zones"],
        "root_causes": session["root_causes"],
    }


@router.get("/analysis/{analysis_id}/forecasts")
def get_analysis_forecasts(analysis_id: str) -> dict[str, Any]:
    """Return 7-day, 14-day, and 30-day cash forecasts for an analysis."""
    session = get_analysis_by_id(analysis_id)
    return {
        "analysis_id": session["analysis_id"],
        "forecasts": session["forecasts"],
    }


def _execute_simulation(analysis_id: str, payload: SimulateRequest) -> dict[str, Any]:
    """Shared implementation for running a non-mutating what-if simulation."""
    session = get_analysis_by_id(analysis_id)
    interventions_dicts = [i.model_dump(exclude_none=True) for i in payload.interventions]

    sim_result = run_what_if_simulation(
        normalized_records=session["normalized_transactions"],
        opening_cash=session["opening_cash"],
        safety_reserve=session["safety_reserve"],
        as_of_date=session["as_of_date"],
        interventions=interventions_dicts,
        scenario_name=payload.scenario_name,
    )
    persisted_sim = persist_scenario_simulation(
        analysis_id=session["analysis_id"],
        simulation_result=sim_result,
    )
    return persisted_sim


@router.post("/simulate")
def simulate_scenario_root(payload: SimulateRequest) -> dict[str, Any]:
    """Run a non-mutating what-if simulation using `analysis_id` in the JSON body."""
    target_analysis_id = payload.analysis_id or DEMO_ANALYSIS_ID
    return _execute_simulation(target_analysis_id, payload)


@router.post("/analysis/{analysis_id}/simulate")
def simulate_scenario_by_path(analysis_id: str, payload: SimulateRequest) -> dict[str, Any]:
    """Run a non-mutating what-if simulation for a path-specified `analysis_id`."""
    return _execute_simulation(analysis_id, payload)

