"""Analysis router — dashboard payload and partial analysis endpoints."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime, timedelta
import math
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_manager
from api.job_manager import JobManager
from src.services.dashboard_service import (
    DashboardError,
    DashboardPayload,
    build_dashboard_payload,
    delete_shareholder_meeting_override,
    get_event_calendar,
    get_institutional_cost,
    get_dividend_history_with_pe,
    get_industry_per_table,
    get_monthly_revenue,
    get_valuation,
    upsert_shareholder_meeting_override,
)

router = APIRouter(tags=["analysis"])


class ShareholderMeetingOverrideBody(BaseModel):
    symbol: str
    date: str
    meeting_type: str


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return _to_jsonable(asdict(value))
    if isinstance(value, pd.DataFrame):
        records = value.to_dict(orient="records")
        return [_to_jsonable(row) for row in records]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if pd.isna(value):
        return None
    return value


def _serialize_payload(payload: DashboardPayload) -> dict[str, Any]:
    return {
        "symbol": payload.symbol,
        "market": payload.market,
        "subject_name": payload.subject_name,
        "analysis_time": payload.analysis_time,
        "ai_enabled": payload.ai_enabled,
        "daily_df": _to_jsonable(payload.daily_df),
        "technical": _to_jsonable(payload.technical),
        "candle_patterns": _to_jsonable(payload.candle_patterns),
        "chart_patterns": _to_jsonable(payload.chart_patterns),
        "multi_timeframe": _to_jsonable(payload.multi_timeframe),
        "quote": _to_jsonable(payload.quote),
        "bid_ask": _to_jsonable(payload.bid_ask),
        "chip": _to_jsonable(payload.chip),
        "chip_recent_df": _to_jsonable(payload.chip_recent_df),
        "chip_error": payload.chip_error,
        "intraday_df": _to_jsonable(payload.intraday_df),
        "intraday_snapshot": _to_jsonable(payload.intraday_snapshot),
        "intraday_error": payload.intraday_error,
        "analysis": _to_jsonable(payload.analysis),
    }


def _resolve_payload_or_error(
    symbol: str,
    market: str,
    bars: int,
) -> DashboardPayload:
    result = build_dashboard_payload(symbol=symbol, market=market, bars=bars)
    if isinstance(result, DashboardError):
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": result.code, "message": result.message}},
        )
    return result


@router.get("/api/dashboard/payload")
async def get_dashboard_payload(
    symbol: str,
    market: str = "tw",
    bars: int = 250,
    manager: JobManager = Depends(get_manager),
) -> dict[str, Any]:
    """Aggregated dashboard payload endpoint."""
    if manager.is_write_locked():
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "WRITE_LOCK_BUSY",
                    "message": "目前有其他資料操作正在進行，請稍後再試",
                }
            },
        )
    acquired = await manager.acquire_write_lock()
    if not acquired:
        raise HTTPException(
            status_code=409,
            detail={
                "error": {
                    "code": "WRITE_LOCK_BUSY",
                    "message": "目前有其他資料操作正在進行，請稍後再試",
                }
            },
        )
    try:
        payload = _resolve_payload_or_error(symbol=symbol, market=market, bars=bars)
    finally:
        manager.release_write_lock()

    return {
        "data": _serialize_payload(payload),
        "meta": {"symbol": payload.symbol, "market": payload.market},
    }


@router.get("/api/analysis/p11/valuation")
def get_p11_valuation(
    symbol: str,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_valuation(symbol=symbol, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_valuation", "symbol": symbol, "market": market}}


@router.get("/api/analysis/p11/monthly-revenue")
def get_p11_monthly_revenue(
    symbol: str,
    months: int = 12,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_monthly_revenue(symbol=symbol, months=months, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_monthly_revenue", "symbol": symbol, "market": market}}


@router.get("/api/analysis/p11/dividend-history")
def get_p11_dividend_history(
    symbol: str,
    count: int = 5,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_dividend_history_with_pe(symbol=symbol, count=count, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_dividend_history", "symbol": symbol, "market": market}}


@router.get("/api/analysis/p11/industry-per")
def get_p11_industry_per(
    symbol: str,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_industry_per_table(symbol=symbol, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_industry_per", "symbol": symbol, "market": market}}


@router.get("/api/analysis/p11/institutional-cost")
def get_p11_institutional_cost(
    symbol: str,
    days: int = 30,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_institutional_cost(symbol=symbol, days=days, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_institutional_cost", "symbol": symbol, "market": market}}


@router.get("/api/analysis/p11/event-calendar")
def get_p11_event_calendar(
    symbol: str,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = get_event_calendar(symbol=symbol, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc

    return {"data": _to_jsonable(data), "meta": {"section": "p11_event_calendar", "symbol": symbol, "market": market}}


def _validate_override_payload(payload: ShareholderMeetingOverrideBody) -> None:
    if payload.meeting_type not in {"常會", "臨時會"}:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_MEETING_TYPE", "message": "meeting_type must be 常會 or 臨時會"}},
        )

    try:
        parsed = datetime.strptime(payload.date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_DATE", "message": "date must be YYYY-MM-DD"}},
        ) from exc

    today = datetime.now().date()
    threshold = today - timedelta(days=365)
    if parsed < threshold:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "DATE_TOO_OLD", "message": "date cannot be earlier than one year before today"}},
        )


@router.post("/api/analysis/p11/shareholder-meeting/override")
def post_shareholder_meeting_override(
    body: ShareholderMeetingOverrideBody,
    market: str = "tw",
) -> dict[str, Any]:
    _validate_override_payload(body)
    try:
        data = upsert_shareholder_meeting_override(
            symbol=body.symbol,
            date=body.date,
            meeting_type=body.meeting_type,
            market=market,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc
    return {"data": _to_jsonable(data), "meta": {"section": "p11_shareholder_meeting_override", "symbol": body.symbol, "market": market}}


@router.delete("/api/analysis/p11/shareholder-meeting/override")
def delete_p11_shareholder_meeting_override(
    symbol: str,
    market: str = "tw",
) -> dict[str, Any]:
    try:
        data = delete_shareholder_meeting_override(symbol=symbol, market=market)
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={"error": {"code": "P11_US_UNSUPPORTED", "message": str(exc)}},
        ) from exc
    return {"data": _to_jsonable(data), "meta": {"section": "p11_shareholder_meeting_override_delete", "symbol": symbol, "market": market}}


@router.get("/api/analysis/{section}")
def get_analysis_section(
    section: str,
    symbol: str,
    market: str = "tw",
    bars: int = 250,
) -> dict[str, Any]:
    """Partial analysis endpoint for section-level refresh."""
    payload = _resolve_payload_or_error(symbol=symbol, market=market, bars=bars)
    section_map: dict[str, Any] = {
        "technical": payload.technical,
        "pattern": {
            "candle_patterns": payload.candle_patterns,
            "chart_patterns": payload.chart_patterns,
            "multi_timeframe": payload.multi_timeframe,
        },
        "chip": {
            "chip": payload.chip,
            "chip_recent_df": payload.chip_recent_df,
            "chip_error": payload.chip_error,
            "bid_ask": payload.bid_ask,
        },
        "daily": payload.daily_df,
    }
    if section not in section_map:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "UNKNOWN_SECTION",
                    "message": f"Unknown analysis section: {section}",
                }
            },
        )

    return {
        "data": _to_jsonable(section_map[section]),
        "meta": {"section": section, "symbol": payload.symbol, "market": payload.market},
    }
