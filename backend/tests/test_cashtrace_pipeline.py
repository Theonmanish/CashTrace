"""Comprehensive test suite for CashTrace Financial Engine and FastAPI Backend."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]
for p in (str(REPO_ROOT), str(BACKEND_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi.testclient import TestClient

from app.main import app
from app.services.demo_data import get_msme_demo_transactions
from financial_engine import (
    ValidationError,
    detect_dead_zones,
    normalize_records,
    parse_csv_content,
    reconstruct_cash_timeline,
    run_full_analysis,
    run_what_if_simulation,
    validate_records,
)


def test_hybrid_ledger_and_overdue_invoice_rule() -> None:
    """
    Verify:
    1) Positive internal amounts and normalized 'inflow'/'outflow' types.
    2) Overdue unpaid invoice (due_date in past, actual_payment_date empty)
       is classified as SCHEDULED and NEVER enters historical cash reconstruction.
    """
    raw = [
        {
            "row_id": "T1",
            "date": "2026-10-01",
            "type": "credit",
            "amount": "₹50,000",
        },
        {
            "row_id": "T2",
            "date": "2026-10-02",
            "type": "debit",
            "amount": "-20000",
            "due_date": "2026-10-03",
            "actual_payment_date": "2026-10-05",
        },
        {
            "row_id": "T3-OVERDUE-UNPAID",
            "date": "2026-10-01",
            "type": "inflow",
            "amount": 999999,
            "due_date": "2026-10-02",
            "actual_payment_date": None,
        },
    ]

    normalized, as_of = normalize_records(raw)
    assert as_of.isoformat() == "2026-10-05"

    by_id = {r["row_id"]: r for r in normalized}
    assert by_id["T1"]["type"] == "inflow"
    assert by_id["T1"]["amount"] == 50000.0
    assert by_id["T1"]["ledger_state"] == "SETTLED"
    assert by_id["T1"]["effective_date"] == "2026-10-01"

    assert by_id["T2"]["type"] == "outflow"
    assert by_id["T2"]["amount"] == 20000.0  # strictly positive internal amount
    assert by_id["T2"]["signed_amount"] == -20000.0
    assert by_id["T2"]["ledger_state"] == "SETTLED"
    assert by_id["T2"]["effective_date"] == "2026-10-05"

    # Overdue unpaid invoice must be SCHEDULED and excluded from historical cash
    assert by_id["T3-OVERDUE-UNPAID"]["ledger_state"] == "SCHEDULED"
    assert by_id["T3-OVERDUE-UNPAID"]["is_overdue"] is True

    recon = reconstruct_cash_timeline(normalized, opening_cash=100000.0, as_of_date=as_of)
    assert recon["total_inflows"] == 50000.0
    assert recon["total_outflows"] == 20000.0
    assert recon["final_closing_cash"] == 130000.0
    assert (
        recon["opening_cash"] + recon["total_inflows"] - recon["total_outflows"]
        == recon["final_closing_cash"]
    )


def test_dead_zone_requires_at_least_two_consecutive_days() -> None:
    """Verify a 1-day dip below safety reserve is NOT a dead zone, while >=2 days IS."""
    timeline = [
        {"date": "2026-10-01", "closing_cash": 120000.0},
        {"date": "2026-10-02", "closing_cash": 85000.0},  # 1-day dip only
        {"date": "2026-10-03", "closing_cash": 110000.0},
        {"date": "2026-10-04", "closing_cash": 60000.0},  # Day 1 of dead zone
        {"date": "2026-10-05", "closing_cash": 40000.0},  # Day 2 of dead zone
        {"date": "2026-10-06", "closing_cash": 105000.0},
    ]
    dz = detect_dead_zones(timeline, safety_reserve=100000.0)
    assert len(dz) == 1
    assert dz[0]["start_date"] == "2026-10-04"
    assert dz[0]["end_date"] == "2026-10-05"
    assert dz[0]["duration"] == 2
    assert dz[0]["minimum_cash"] == 40000.0
    assert dz[0]["absolute_shortfall"] == 60000.0
    assert dz[0]["shortfall_percentage"] == 60.0
    assert dz[0]["severity"] in {"HIGH", "CRITICAL"}
    assert dz[0]["db_severity"] in {"critical", "fatal"}


def test_full_pipeline_and_non_mutating_simulation() -> None:
    """Verify full analysis + non-mutating what-if simulations on the MSME demo dataset."""
    demo_rows = get_msme_demo_transactions()
    analysis = run_full_analysis(
        raw_records=demo_rows,
        opening_cash=220000.0,
        safety_reserve=100000.0,
    )

    assert analysis["summary"]["invariant_verified"] is True
    assert len(analysis["dead_zones"]) >= 1
    dz0 = analysis["dead_zones"][0]
    assert dz0["start_date"] == "2026-10-10"
    assert dz0["end_date"] == "2026-10-15"
    assert dz0["duration"] == 6

    root_cause_cats = {rc["category"] for rc in dz0["root_causes"]}
    assert "CUSTOMER_PAYMENT_DELAY" in root_cause_cats
    assert "SUPPLIER_PAYMENT_CLUSTER" in root_cause_cats

    # Snapshot original transactions to verify simulation does NOT mutate them
    snapshot_before = copy.deepcopy(analysis["normalized_transactions"])

    sim = run_what_if_simulation(
        normalized_records=analysis["normalized_transactions"],
        opening_cash=analysis["opening_cash"],
        safety_reserve=analysis["safety_reserve"],
        as_of_date=analysis["as_of_date"],
        interventions=[
            {
                "type": "CUSTOMER_PAYMENT_EARLIER",
                "transaction_id": "TXN-1006",
                "new_date": "2026-10-08",
            },
            {
                "type": "SUPPLIER_PAYMENT_SPLIT",
                "transaction_id": "TXN-1010",
                "split_count": 2,
                "split_interval_days": 12,
            },
        ],
    )

    assert analysis["normalized_transactions"] == snapshot_before
    assert sim["comparison"]["simulated_dead_zones_count"] == 0
    assert sim["comparison"]["min_cash_improvement"] > 0


def test_fastapi_endpoints_end_to_end() -> None:
    """Verify GET /api/demo, POST /api/analyze (JSON & CSV), GET /api/analysis/{id}, POST /api/simulate."""
    client = TestClient(app)

    # 1. Health & Demo
    r_health = client.get("/health")
    assert r_health.status_code == 200

    r_demo = client.get("/api/demo")
    assert r_demo.status_code == 200
    demo_data = r_demo.json()
    assert "analysis_id" in demo_data
    assert len(demo_data["dead_zones"]) >= 1
    assert "7_days" in demo_data["forecasts"]["horizons"]
    assert "14_days" in demo_data["forecasts"]["horizons"]
    assert "30_days" in demo_data["forecasts"]["horizons"]

    # 2. CSV upload via POST /api/analyze
    sample_csv_resp = client.get("/api/demo/sample-csv")
    assert sample_csv_resp.status_code == 200
    csv_bytes = sample_csv_resp.text.encode("utf-8")

    r_upload = client.post(
        "/api/analyze",
        data={"opening_cash": "220000", "safety_reserve": "100000"},
        files={"file": ("msme_ledger.csv", csv_bytes, "text/csv")},
    )
    assert r_upload.status_code == 200
    uploaded_analysis = r_upload.json()
    analysis_id = uploaded_analysis["analysis_id"]

    # 3. Retrieve analysis by ID
    r_get = client.get(f"/api/analysis/{analysis_id}")
    assert r_get.status_code == 200
    assert r_get.json()["analysis_id"] == analysis_id

    # 4. Run What-If simulation via POST /api/simulate
    r_sim = client.post(
        "/api/simulate",
        json={
            "analysis_id": analysis_id,
            "scenario_name": "Collect Early + Lower Buffer",
            "interventions": [
                {
                    "type": "CUSTOMER_PAYMENT_EARLIER",
                    "transaction_id": "TXN-1006",
                    "new_date": "2026-10-08",
                },
                {
                    "type": "SAFETY_RESERVE_CHANGED",
                    "new_safety_reserve": 90000,
                },
            ],
        },
    )
    assert r_sim.status_code == 200
    sim_json = r_sim.json()
    assert sim_json["comparison"]["simulated_dead_zones_count"] == 0


def test_post_demo_analyze_returns_analysis_id_for_session_endpoints() -> None:
    """Verify POST /api/demo/analyze returns a non-empty analysis_id usable by session endpoints."""
    client = TestClient(app)

    r_demo_post = client.post("/api/demo/analyze")
    assert r_demo_post.status_code == 200
    body = r_demo_post.json()

    assert "analysis_id" in body
    assert isinstance(body["analysis_id"], str)
    assert len(body["analysis_id"].strip()) > 0
    # Ensure analysis_id is the first key in the serialized JSON response
    assert list(body.keys())[0] == "analysis_id"

    demo_analysis_id = body["analysis_id"]

    # Verify GET /api/analysis/{analysis_id} works with the returned analysis_id
    r_get = client.get(f"/api/analysis/{demo_analysis_id}")
    assert r_get.status_code == 200
    assert r_get.json()["analysis_id"] == demo_analysis_id

    # Verify POST /api/analysis/{analysis_id}/simulate works with the returned analysis_id
    r_sim = client.post(
        f"/api/analysis/{demo_analysis_id}/simulate",
        json={
            "scenario_name": "Demo Session Simulation",
            "interventions": [
                {
                    "type": "CUSTOMER_PAYMENT_EARLIER",
                    "transaction_id": "TXN-1006",
                    "new_date": "2026-10-08",
                }
            ],
        },
    )
    assert r_sim.status_code == 200
    assert r_sim.json()["analysis_id"] == demo_analysis_id

