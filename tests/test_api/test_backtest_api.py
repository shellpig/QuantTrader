"""Tests for backtest API endpoints (Phase 10-E-1).

Verifies Job lifecycle for backtest_run:
  - POST /api/jobs { type: "backtest_run" } creates and returns job_id
  - Write lock: second concurrent backtest_run → 409
  - GET /api/jobs/{id}/result returns full result envelope after complete
  - SSE progress events contain phase field
  - GET /api/config/strategies returns preset list
  - Invalid strategy_preset_index → job error INVALID_PARAMS
  - Unknown symbol → job error NO_DATA or FETCH_FAILED
  - Cancelled job with partial result → GET /api/jobs/{id}/result 200 (not 409)
  - finish_cancelled_job stores result + closes queue
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.job_manager import get_job_manager

client = TestClient(app)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_MINIMAL_PRESET = {"name": "MA20_MA60", "type": "moving_average_cross", "params": {"short_window": 20, "long_window": 60}}
_MINIMAL_PRESETS = [_MINIMAL_PRESET]

_MOCK_RESULT_PAYLOAD = {
    "symbol": "2330",
    "market": "tw",
    "currency": "TWD",
    "engine": "vectorized",
    "strategy_type": "moving_average_cross",
    "strategy_params": {"short_window": 20, "long_window": 60},
    "metrics": {
        "total_trades": 5,
        "total_return": 0.2,
        "annual_return": 0.05,
        "max_drawdown": -0.1,
        "max_drawdown_start": "2022-01-01",
        "max_drawdown_end": "2022-06-01",
        "sharpe_ratio": 0.8,
        "win_rate": 0.6,
        "profit_factor": 1.5,
    },
    "equity_curve": [{"date": "2020-01-02", "value": 1_000_000}],
    "trades": [
        {
            "entry_date": "2020-03-15",
            "exit_date": "2020-05-20",
            "side": "long",
            "entry_price": 280.0,
            "exit_price": 310.0,
            "shares": 1000,
            "pnl": 30000.0,
            "return_pct": 0.107,
        }
    ],
    "signals": [
        {"date": "2020-03-15", "side": "buy", "price": 280.0},
        {"date": "2020-05-20", "side": "sell", "price": 310.0},
    ],
    "price_data": [{"date": "2020-01-02", "open": 330, "high": 335, "low": 328, "close": 333, "volume": 10000}],
    "dca_warning": None,
}

_MOCK_BATCH_PAYLOAD = {
    "symbol": "2330",
    "market": "tw",
    "currency": "TWD",
    "engine": "vectorized",
    "start_date": "2020-01-01",
    "end_date": "2024-12-31",
    "total_presets": 2,
    "completed_presets": 2,
    "success_count": 1,
    "failed_count": 1,
    "price_data": [{"date": "2020-01-02", "open": 330, "high": 335, "low": 328, "close": 333, "volume": 10000}],
    "summaries": [
        {
            "preset_index": 0,
            "preset_name": "MA20_MA60",
            "strategy_type": "moving_average_cross",
            "strategy_params": {"short_window": 20, "long_window": 60},
            "total_return": 0.2,
            "annual_return": 0.05,
            "max_drawdown": 0.1,
            "sharpe_ratio": 0.8,
            "win_rate": 0.6,
            "profit_factor": 1.5,
            "total_trades": 5,
            "error": None,
            "detail": {
                "symbol": "2330",
                "market": "tw",
                "currency": "TWD",
                "engine": "vectorized",
                "strategy_type": "moving_average_cross",
                "strategy_params": {"short_window": 20, "long_window": 60},
                "metrics": {
                    "total_trades": 5,
                    "total_return": 0.2,
                    "annual_return": 0.05,
                    "max_drawdown": 0.1,
                    "max_drawdown_start": "2022-01-01",
                    "max_drawdown_end": "2022-06-01",
                    "sharpe_ratio": 0.8,
                    "win_rate": 0.6,
                    "profit_factor": 1.5,
                },
                "equity_curve": [{"date": "2020-01-02", "value": 1000000}],
                "trades": [],
                "signals": [],
                "dca_warning": None,
            },
        },
        {
            "preset_index": 1,
            "preset_name": "定期定額",
            "strategy_type": "dollar_cost_averaging",
            "strategy_params": {"monthly_day": 5, "monthly_amount": 10000},
            "total_return": None,
            "annual_return": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
            "win_rate": None,
            "profit_factor": None,
            "total_trades": 0,
            "error": "DCA 不支援批次比較（請至單次回測使用）",
            "detail": None,
        },
    ],
}


def _reset_manager() -> None:
    import api.job_manager as jm
    jm._job_manager = None


def _wait_for_job(job_id: str, timeout: float = 5.0) -> dict:
    """Poll job status until complete / error / cancelled (or timeout)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(f"/api/jobs/{job_id}")
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] in ("complete", "error", "cancelled"):
            return body
        time.sleep(0.05)
    return client.get(f"/api/jobs/{job_id}").json()


def _wait_for_result(job_id: str, timeout: float = 5.0):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"/api/jobs/{job_id}/result")
        if last.status_code == 200:
            return last
        time.sleep(0.05)
    return last


# ---------------------------------------------------------------------------
# 1. POST /api/jobs backtest_run creates job
# ---------------------------------------------------------------------------


def test_backtest_run_creates_job() -> None:
    _reset_manager()
    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS),
        patch("src.services.backtest_service.run_backtest_job", return_value=MagicMock(
            symbol="2330", market="tw", currency="TWD", engine="vectorized",
            strategy_type="moving_average_cross", strategy_params={},
            result=None, dca_result=None, data=pd.DataFrame(), dca_warning=None, error=None,
        )),
        patch("src.services.backtest_service.serialize_backtest_result", return_value=_MOCK_RESULT_PAYLOAD),
    ):
        resp = client.post("/api/jobs", json={
            "type": "backtest_run",
            "params": {
                "market": "tw", "symbol": "2330",
                "start_date": "2020-01-01", "end_date": "2024-12-31",
                "strategy_preset_index": 0, "engine": "vectorized",
                "initial_capital": 1_000_000,
            },
        })
    assert resp.status_code == 201
    body = resp.json()
    assert "job_id" in body
    assert len(body["job_id"]) > 0
    assert body["type"] == "backtest_run"


# ---------------------------------------------------------------------------
# 2. _WRITE_JOB_TYPES contains backtest_run → 409 when lock held
# ---------------------------------------------------------------------------


def test_backtest_run_write_lock_409() -> None:
    _reset_manager()
    manager = get_job_manager()

    async def _hold() -> None:
        await manager._write_lock.acquire()

    asyncio.run(_hold())
    try:
        resp = client.post("/api/jobs", json={"type": "backtest_run", "params": {}})
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "WRITE_LOCK_BUSY"
    finally:
        manager.release_write_lock()


# ---------------------------------------------------------------------------
# 3. GET /api/jobs/{id}/result returns full result after complete
# ---------------------------------------------------------------------------


def test_backtest_run_result_after_complete() -> None:
    _reset_manager()
    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS),
        patch("src.services.backtest_service.run_backtest_job", return_value=MagicMock(
            symbol="2330", market="tw", currency="TWD", engine="vectorized",
            strategy_type="moving_average_cross", strategy_params={},
            result=None, dca_result=None, data=pd.DataFrame(), dca_warning=None, error=None,
        )),
        patch("src.services.backtest_service.serialize_backtest_result", return_value=_MOCK_RESULT_PAYLOAD),
    ):
        resp = client.post("/api/jobs", json={
            "type": "backtest_run",
            "params": {
                "market": "tw", "symbol": "2330",
                "start_date": "2020-01-01", "end_date": "2024-12-31",
                "strategy_preset_index": 0, "engine": "vectorized",
            },
        })
        job_id = resp.json()["job_id"]
        _wait_for_job(job_id)

        result_resp = client.get(f"/api/jobs/{job_id}/result")

    assert result_resp.status_code == 200
    data = result_resp.json()["data"]
    assert "metrics" in data
    assert "equity_curve" in data
    assert "trades" in data
    assert "signals" in data
    assert "price_data" in data
    assert data["currency"] == "TWD"


# ---------------------------------------------------------------------------
# 4. SSE progress event contains phase field
# ---------------------------------------------------------------------------


def test_backtest_run_sse_progress_phase() -> None:
    _reset_manager()
    # Use the actual job manager to push a synthetic event and verify format
    manager = get_job_manager()

    async def _push() -> None:
        job = await manager.create_job("backtest_run", {})
        manager.push_event(job.id, "progress", {"status": "running", "phase": "loading_data"})
        manager._close_event_queue(job.id)
        return job.id

    job_id = asyncio.run(_push())
    # Verify via SSE stream (consume one event)
    with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
        for line in stream.iter_lines():
            if line.startswith("data:"):
                import json
                payload = json.loads(line[5:].strip())
                assert "phase" in payload
                break


# ---------------------------------------------------------------------------
# 5. GET /api/config/strategies returns preset list
# ---------------------------------------------------------------------------


def test_get_strategies_returns_list() -> None:
    _reset_manager()
    resp = client.get("/api/config/strategies")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
    assert len(body["data"]) > 0
    preset = body["data"][0]
    assert "name" in preset
    assert "type" in preset


# ---------------------------------------------------------------------------
# 6. Invalid strategy_preset_index → INVALID_PARAMS
# ---------------------------------------------------------------------------


def test_invalid_strategy_preset_index_fails_job() -> None:
    _reset_manager()
    with patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS):
        resp = client.post("/api/jobs", json={
            "type": "backtest_run",
            "params": {"market": "tw", "symbol": "2330", "strategy_preset_index": 999},
        })
        job_id = resp.json()["job_id"]
        final = _wait_for_job(job_id)

    assert final["status"] == "error"
    result_resp = client.get(f"/api/jobs/{job_id}/result")
    assert result_resp.status_code == 409  # error state, not complete


# ---------------------------------------------------------------------------
# 7. Unknown symbol → NO_DATA or FETCH_FAILED in job error
# ---------------------------------------------------------------------------


def test_unknown_symbol_fails_job() -> None:
    from src.services.backtest_service import BacktestServiceError

    _reset_manager()
    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS),
        patch("src.services.backtest_service.run_backtest_job", return_value=BacktestServiceError(
            code="NO_DATA", message="UNKNOWN_SYMBOL_XYZ 無可用日線資料。"
        )),
    ):
        resp = client.post("/api/jobs", json={
            "type": "backtest_run",
            "params": {
                "market": "tw", "symbol": "UNKNOWN_SYMBOL_XYZ",
                "start_date": "2020-01-01", "end_date": "2024-12-31",
                "strategy_preset_index": 0,
            },
        })
        job_id = resp.json()["job_id"]
        final = _wait_for_job(job_id)

    assert final["status"] == "error"


# ---------------------------------------------------------------------------
# 8. Cancelled job with partial result → 200 (not 409)
# ---------------------------------------------------------------------------


def test_cancelled_job_with_partial_result_returns_200() -> None:
    _reset_manager()
    manager = get_job_manager()

    partial = {"symbol": "2330", "partial": True, "summaries": []}

    async def _setup() -> str:
        job = await manager.create_job("backtest_run", {})
        job.status = "cancelled"
        manager.finish_cancelled_job(job.id, result=partial)
        return job.id

    job_id = asyncio.run(_setup())
    resp = client.get(f"/api/jobs/{job_id}/result")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["status"] == "cancelled"
    assert body["data"]["partial"] is True


# ---------------------------------------------------------------------------
# 9. finish_cancelled_job stores result and closes event queue
# ---------------------------------------------------------------------------


def test_finish_cancelled_job_closes_queue() -> None:
    _reset_manager()
    manager = get_job_manager()
    partial = {"test": "partial"}

    async def _run() -> None:
        job = await manager.create_job("backtest_run", {})
        job.status = "cancelled"
        manager.finish_cancelled_job(job.id, result=partial)
        retrieved = manager.get_job(job.id)
        assert retrieved is not None
        assert retrieved.status == "cancelled"
        assert retrieved.result == partial

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 10-E-2 backtest_batch tests
# ---------------------------------------------------------------------------


def test_backtest_batch_creates_job_and_returns_summaries() -> None:
    _reset_manager()
    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS),
        patch("src.services.backtest_service.run_batch_backtest_job", return_value=_MOCK_BATCH_PAYLOAD),
    ):
        resp = client.post("/api/jobs", json={
            "type": "backtest_batch",
            "params": {
                "market": "tw",
                "symbol": "2330",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "strategy_preset_indices": [0],
            },
        })
        assert resp.status_code == 201
        job_id = resp.json()["job_id"]
        final = _wait_for_job(job_id)
        assert final["status"] == "complete"
        result = client.get(f"/api/jobs/{job_id}/result")
        assert result.status_code == 200
        data = result.json()["data"]
        assert "summaries" in data
        assert isinstance(data["summaries"], list)
        assert len(data["summaries"]) == 1


def test_backtest_batch_dca_summary_has_error() -> None:
    _reset_manager()
    manager = get_job_manager()

    payload = dict(_MOCK_BATCH_PAYLOAD)

    async def _setup() -> str:
        job = await manager.create_job("backtest_batch", {})
        manager.complete_job(job.id, result=payload)
        return job.id

    job_id = asyncio.run(_setup())
    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    summaries = result.json()["data"]["summaries"]
    dca_rows = [s for s in summaries if s["strategy_type"] == "dollar_cost_averaging"]
    assert len(dca_rows) == 1
    assert dca_rows[0]["error"] is not None


def test_backtest_batch_cancel_keeps_partial_result() -> None:
    _reset_manager()
    manager = get_job_manager()

    partial = dict(_MOCK_BATCH_PAYLOAD)
    partial["completed_presets"] = 3
    partial["total_presets"] = 8
    partial["summaries"] = partial["summaries"][:1]

    async def _setup() -> str:
        job = await manager.create_job("backtest_batch", {})
        job.status = "cancelled"
        manager.finish_cancelled_job(job.id, result=partial)
        return job.id

    job_id = asyncio.run(_setup())
    result = client.get(f"/api/jobs/{job_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["meta"]["status"] == "cancelled"
    assert body["data"]["completed_presets"] == 3
    assert body["data"]["total_presets"] == 8


def test_backtest_batch_csv_export_returns_blob() -> None:
    _reset_manager()
    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=_MINIMAL_PRESETS),
        patch("src.services.backtest_service.run_batch_backtest_job", return_value=_MOCK_BATCH_PAYLOAD),
    ):
        create = client.post("/api/jobs", json={
            "type": "backtest_batch",
            "params": {
                "market": "tw",
                "symbol": "2330",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "strategy_preset_indices": [0],
            },
        })
        job_id = create.json()["job_id"]
        _wait_for_job(job_id)
        csv_resp = client.get(f"/api/jobs/{job_id}/result?format=csv")

    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers.get("content-type", "")
    disposition = csv_resp.headers.get("content-disposition", "")
    assert "attachment" in disposition
    assert "batch_2330_" in disposition


def test_backtest_batch_sse_progress_per_preset() -> None:
    _reset_manager()
    presets = [
        {"name": "MA20_MA60", "type": "moving_average_cross", "params": {"short_window": 20, "long_window": 60}},
        {"name": "RSI_14", "type": "rsi", "params": {"period": 14, "oversold": 30, "overbought": 70}},
    ]

    def _one_preset_payload(*, presets: list[dict], **_: object) -> dict:
        p = presets[0]
        return {
            "symbol": "2330",
            "market": "tw",
            "currency": "TWD",
            "engine": "vectorized",
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "price_data": [],
            "summaries": [{
                "preset_index": 0,
                "preset_name": p["name"],
                "strategy_type": p["type"],
                "strategy_params": p["params"],
                "total_return": 0.1,
                "annual_return": 0.03,
                "max_drawdown": 0.1,
                "sharpe_ratio": 0.7,
                "win_rate": 0.5,
                "profit_factor": 1.2,
                "total_trades": 3,
                "error": None,
                "detail": None,
            }],
        }

    with (
        patch("src.services.backtest_service.list_strategy_presets", return_value=presets),
        patch("src.services.backtest_service.run_batch_backtest_job", side_effect=_one_preset_payload),
    ):
        create = client.post("/api/jobs", json={
            "type": "backtest_batch",
            "params": {
                "market": "tw",
                "symbol": "2330",
                "start_date": "2020-01-01",
                "end_date": "2024-12-31",
                "strategy_preset_indices": [0, 1],
            },
        })
        job_id = create.json()["job_id"]
        _wait_for_job(job_id, timeout=8.0)

        progress_payloads: list[dict] = []
        with client.stream("GET", f"/api/jobs/{job_id}/events") as stream:
            current_event: str | None = None
            for line in stream.iter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    continue
                if line.startswith("data:"):
                    raw = line.split(":", 1)[1].strip()
                    if current_event == "progress":
                        import json
                        progress_payloads.append(json.loads(raw))

        assert len(progress_payloads) >= 2
        assert all("current" in p and "total" in p for p in progress_payloads)
        assert {p["preset_name"] for p in progress_payloads if "preset_name" in p} >= {"MA20_MA60", "RSI_14"}
