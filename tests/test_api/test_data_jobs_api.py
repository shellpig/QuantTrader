"""Tests for data_update / data_rebuild job types (Phase 10-C-2).

Tests cover:
- POST /api/jobs with data_update / data_rebuild types
- 409 when write lock is held
- SSE endpoint content-type
- _run_data_job logic: success, single failure continues, no-targets error, all-mode
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.job_manager import get_job_manager

client: TestClient = None  # type: ignore[assignment]


def _reset() -> None:
    import api.job_manager as jm
    jm._job_manager = None


@pytest.fixture(autouse=True)
def _isolate_client():
    """Give each test a fresh TestClient so background asyncio tasks cannot leak."""
    global client
    _reset()
    with TestClient(app) as c:
        client = c
        yield


@pytest.fixture(autouse=True)
def _mock_shareholder_refresh():
    with patch("src.services.data_service.refresh_shareholder_meeting_once_per_day", return_value=False):
        yield


# ---------------------------------------------------------------------------
# POST /api/jobs — create data_update / data_rebuild
# ---------------------------------------------------------------------------


@patch("api.routers.jobs._run_job", new_callable=AsyncMock)
def test_create_data_update_job_returns_201(_mock_run: AsyncMock) -> None:
    _reset()
    resp = client.post("/api/jobs", json={"type": "data_update", "params": {"market": "tw", "symbols": ["2330"]}})
    assert resp.status_code == 201
    body = resp.json()
    assert "job_id" in body
    assert body["type"] == "data_update"


@patch("api.routers.jobs._run_job", new_callable=AsyncMock)
def test_create_data_rebuild_job_returns_201(_mock_run: AsyncMock) -> None:
    _reset()
    resp = client.post("/api/jobs", json={"type": "data_rebuild", "params": {"market": "tw", "all": True}})
    assert resp.status_code == 201
    assert resp.json()["type"] == "data_rebuild"


def test_data_update_job_409_when_lock_held() -> None:
    _reset()
    mgr = get_job_manager()

    async def _hold() -> None:
        await mgr._write_lock.acquire()

    asyncio.run(_hold())
    try:
        resp = client.post("/api/jobs", json={"type": "data_update", "params": {}})
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "WRITE_LOCK_BUSY"
    finally:
        mgr.release_write_lock()


def test_data_rebuild_job_409_when_lock_held() -> None:
    _reset()
    mgr = get_job_manager()

    async def _hold() -> None:
        await mgr._write_lock.acquire()

    asyncio.run(_hold())
    try:
        resp = client.post("/api/jobs", json={"type": "data_rebuild", "params": {}})
        assert resp.status_code == 409
    finally:
        mgr.release_write_lock()


# ---------------------------------------------------------------------------
# GET /api/jobs/{id}/events — SSE content type
# ---------------------------------------------------------------------------


def test_sse_endpoint_exists_for_data_job() -> None:
    _reset()
    with patch("src.services.data_service.run_maintenance", return_value=MagicMock()):
        create = client.post("/api/jobs", json={"type": "data_update", "params": {"market": "tw", "symbols": ["2330"]}})
        job_id = create.json()["job_id"]

        # Use streaming=True so we can inspect headers without consuming the full body
        with client.stream("GET", f"/api/jobs/{job_id}/events") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]


def test_sse_endpoint_404_for_unknown_job() -> None:
    _reset()
    resp = client.get("/api/jobs/nonexistent-job-xyz/events")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# _run_data_job logic — tested via asyncio.run directly
# ---------------------------------------------------------------------------


async def _make_test_job(job_type: str, params: dict[str, Any]):
    """Helper: create a real Job in a fresh manager."""
    from api.job_manager import get_job_manager

    mgr = get_job_manager()
    job = await mgr.create_job(job_type, params)
    return mgr, job


def test_data_job_calls_run_maintenance_for_each_symbol() -> None:
    """Runner calls run_maintenance once per symbol."""
    _reset()
    call_log: list[str] = []

    def mock_maintenance(symbol: str, *, rebuild: bool = False, market: str = "tw"):
        call_log.append(symbol)
        mock = MagicMock()
        mock.__class__.__name__ = "MaintenanceReport"
        return mock

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": ["2330", "2317"]})
        with patch("src.services.data_service.run_maintenance", side_effect=mock_maintenance):
            await _run_data_job(mgr, job, job.params)
        assert call_log == ["2330", "2317"]
        assert mgr.get_job(job.id).status == "complete"  # type: ignore[union-attr]
        assert mgr.get_job(job.id).result["succeeded"] == ["2330", "2317"]  # type: ignore[union-attr, index]

    asyncio.run(run())


def test_data_job_single_failure_does_not_abort_batch() -> None:
    """If one symbol fails, the rest still process."""
    _reset()

    def mock_maintenance(symbol: str, *, rebuild: bool = False, market: str = "tw"):
        if symbol == "2317":
            raise RuntimeError("mock fetch error")
        mock = MagicMock()
        return mock

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": ["2330", "2317", "2454"]})
        with patch("src.services.data_service.run_maintenance", side_effect=mock_maintenance):
            await _run_data_job(mgr, job, job.params)
        result = mgr.get_job(job.id).result  # type: ignore[union-attr]
        assert "2330" in result["succeeded"]
        assert "2454" in result["succeeded"]
        assert any(f["symbol"] == "2317" for f in result["failed"])
        assert mgr.get_job(job.id).status == "complete"  # type: ignore[union-attr]

    asyncio.run(run())


def test_data_job_no_targets_fails_with_NO_TARGETS() -> None:
    """Empty symbols list → job fails with code NO_TARGETS."""
    _reset()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": []})
        await _run_data_job(mgr, job, job.params)
        j = mgr.get_job(job.id)
        assert j is not None
        assert j.status == "error"
        assert j.error is not None
        assert j.error["code"] == "NO_TARGETS"

    asyncio.run(run())


def test_data_job_all_mode_fetches_symbol_list() -> None:
    """When params.all=True, runner calls list_symbols to get all targets."""
    _reset()
    fetched: list[str] = []

    def mock_list(market: str = "tw") -> list[dict]:
        return [{"symbol": "2330"}, {"symbol": "2317"}]

    def mock_maintenance(symbol: str, *, rebuild: bool = False, market: str = "tw"):
        fetched.append(symbol)
        return MagicMock()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "all": True})
        with (
            patch("src.services.data_service.list_symbols", side_effect=mock_list),
            patch("src.services.data_service.run_maintenance", side_effect=mock_maintenance),
        ):
            await _run_data_job(mgr, job, job.params)
        assert "2330" in fetched
        assert "2317" in fetched

    asyncio.run(run())


def test_data_job_rebuild_passes_rebuild_flag() -> None:
    """data_rebuild job must call run_maintenance with rebuild=True."""
    _reset()
    rebuild_flags: list[bool] = []

    def mock_maintenance(symbol: str, *, rebuild: bool = False, market: str = "tw"):
        rebuild_flags.append(rebuild)
        return MagicMock()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_rebuild", {"market": "tw", "symbols": ["2330"]})
        with patch("src.services.data_service.run_maintenance", side_effect=mock_maintenance):
            await _run_data_job(mgr, job, job.params)
        assert rebuild_flags == [True]

    asyncio.run(run())


def test_data_job_pushes_progress_events() -> None:
    """Runner pushes SSE progress events for each symbol."""
    _reset()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": ["2330"]})
        queue = mgr.get_events_queue(job.id)
        assert queue is not None

        with patch("src.services.data_service.run_maintenance", return_value=MagicMock()):
            await _run_data_job(mgr, job, job.params)

        events: list[dict] = []
        while not queue.empty():
            item = queue.get_nowait()
            if item is not None:
                events.append(item)

        types = {e["type"] for e in events}
        assert "progress" in types
        assert "result" in types

    asyncio.run(run())


def test_data_job_write_lock_released_after_completion() -> None:
    """Write lock must be free after the data job finishes."""
    _reset()

    async def run() -> None:
        from api.routers.jobs import _run_data_job, _run_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": ["2330"]})
        # Manually acquire the write lock (as create_job endpoint would)
        acquired = await mgr.acquire_write_lock()
        assert acquired

        with patch("src.services.data_service.run_maintenance", return_value=MagicMock()):
            await _run_job(mgr, job, job.params)

        assert not mgr.is_write_locked()

    asyncio.run(run())


def test_data_job_triggers_shareholder_refresh_once_after_symbol_loop() -> None:
    _reset()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "tw", "symbols": ["2330", "2317"]})
        with (
            patch("src.services.data_service.run_maintenance", return_value=MagicMock()),
            patch("src.services.data_service.refresh_shareholder_meeting_once_per_day", return_value=True) as mock_refresh,
        ):
            await _run_data_job(mgr, job, job.params)
        assert mock_refresh.call_count == 1
        assert mock_refresh.call_args.args == ("tw",)

    asyncio.run(run())


def test_data_job_us_market_does_not_trigger_shareholder_refresh() -> None:
    _reset()

    async def run() -> None:
        from api.routers.jobs import _run_data_job
        mgr, job = await _make_test_job("data_update", {"market": "us", "symbols": ["AAPL"]})
        with (
            patch("src.services.data_service.run_maintenance", return_value=MagicMock()),
            patch("src.services.data_service.refresh_shareholder_meeting_once_per_day", return_value=True) as mock_refresh,
        ):
            await _run_data_job(mgr, job, job.params)
        assert mock_refresh.call_count == 0

    asyncio.run(run())
