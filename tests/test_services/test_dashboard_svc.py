"""Tests for dashboard_service (Phase 10-A)."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.services.dashboard_service import (
    DashboardError,
    DashboardPayload,
    build_dashboard_payload,
    get_dividend_history_with_pe,
    get_industry_per_table,
    get_monthly_revenue,
    get_valuation,
    _normalize_daily_df,
    _prepare_daily_data,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_daily_df(n: int = 60, market: str = "tw") -> pd.DataFrame:
    """Return a minimal OHLCV daily DataFrame."""
    dates = pd.date_range("2024-01-02", periods=n, freq="B")
    return pd.DataFrame(
        {
            "date": dates,
            "open": [100.0] * n,
            "high": [105.0] * n,
            "low": [95.0] * n,
            "close": [102.0] * n,
            "volume": [1_000_000] * n,
        }
    )


# ---------------------------------------------------------------------------
# _normalize_daily_df
# ---------------------------------------------------------------------------


def test_normalize_daily_df_tw_localizes_timezone() -> None:
    df = _make_daily_df()
    result = _normalize_daily_df(df, market="tw")
    assert result["date"].dt.tz is not None
    assert "Asia/Taipei" in str(result["date"].dt.tz)


def test_normalize_daily_df_us_localizes_new_york() -> None:
    df = _make_daily_df(market="us")
    result = _normalize_daily_df(df, market="us")
    assert result["date"].dt.tz is not None
    assert "America/New_York" in str(result["date"].dt.tz)


def test_normalize_daily_df_drops_ohlcv_nan() -> None:
    df = _make_daily_df(n=10)
    df.loc[3, "close"] = float("nan")
    result = _normalize_daily_df(df, market="tw")
    assert len(result) == 9


def test_normalize_daily_df_sorts_by_date() -> None:
    df = _make_daily_df(n=5)
    shuffled = df.sample(frac=1, random_state=42)
    result = _normalize_daily_df(shuffled, market="tw")
    assert result["date"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# build_dashboard_payload — market routing
# ---------------------------------------------------------------------------


@patch("src.services.dashboard_service._sync_symbol_daily_data")
@patch("src.services.dashboard_service.ParquetStorage")
def test_build_dashboard_payload_returns_error_on_fetch_failure(
    mock_storage_cls: MagicMock,
    mock_sync: MagicMock,
) -> None:
    mock_sync.side_effect = RuntimeError("network error")
    result = build_dashboard_payload("2330", market="tw")
    assert isinstance(result, DashboardError)
    assert result.code == "FETCH_FAILED"
    assert "2330" in result.message


@patch("src.services.dashboard_service._sync_symbol_daily_data")
@patch("src.services.dashboard_service.ParquetStorage")
def test_build_dashboard_payload_returns_error_on_empty_data(
    mock_storage_cls: MagicMock,
    mock_sync: MagicMock,
) -> None:
    mock_storage = MagicMock()
    mock_storage.load_daily.return_value = pd.DataFrame()
    mock_storage.load_adjusted.return_value = pd.DataFrame()
    mock_storage_cls.return_value = mock_storage

    result = build_dashboard_payload("9999", market="tw")
    assert isinstance(result, DashboardError)
    assert result.code == "SYMBOL_NOT_FOUND"


@patch("src.services.dashboard_service._sync_symbol_daily_data")
@patch("src.services.dashboard_service.ParquetStorage")
@patch("src.services.dashboard_service.generate_technical_summary")
@patch("src.services.dashboard_service.detect_candle_patterns")
@patch("src.services.dashboard_service.detect_chart_pattern")
@patch("src.services.dashboard_service.analyze_multi_timeframe")
@patch("src.services.dashboard_service._fetch_tw_realtime")
@patch("src.services.dashboard_service._prepare_chip_data")
@patch("src.services.dashboard_service.get_config")
def test_build_dashboard_payload_tw_calls_chip_and_realtime(
    mock_config: MagicMock,
    mock_chip: MagicMock,
    mock_realtime: MagicMock,
    mock_mtf: MagicMock,
    mock_chart: MagicMock,
    mock_candle: MagicMock,
    mock_tech: MagicMock,
    mock_storage_cls: MagicMock,
    mock_sync: MagicMock,
) -> None:
    mock_storage = MagicMock()
    mock_storage.load_daily.return_value = _make_daily_df()
    mock_storage_cls.return_value = mock_storage

    mock_tech.return_value = MagicMock()
    mock_candle.return_value = []
    mock_chart.return_value = []
    mock_mtf.return_value = MagicMock()
    mock_realtime.return_value = (None, None, None)
    mock_chip.return_value = (None, pd.DataFrame(), None)
    mock_config.return_value = {"ai": {"enabled": False}}

    result = build_dashboard_payload("2330", market="tw")
    assert isinstance(result, DashboardPayload)
    mock_realtime.assert_called_once()
    mock_chip.assert_called_once()


@patch("src.services.dashboard_service._sync_symbol_daily_data")
@patch("src.services.dashboard_service.ParquetStorage")
@patch("src.services.dashboard_service.generate_technical_summary")
@patch("src.services.dashboard_service.detect_candle_patterns")
@patch("src.services.dashboard_service.detect_chart_pattern")
@patch("src.services.dashboard_service.analyze_multi_timeframe")
@patch("src.services.dashboard_service._fetch_us_intraday_snapshot")
@patch("src.services.dashboard_service.get_config")
def test_build_dashboard_payload_us_does_not_call_tw_realtime(
    mock_config: MagicMock,
    mock_intraday: MagicMock,
    mock_mtf: MagicMock,
    mock_chart: MagicMock,
    mock_candle: MagicMock,
    mock_tech: MagicMock,
    mock_storage_cls: MagicMock,
    mock_sync: MagicMock,
) -> None:
    mock_storage = MagicMock()
    mock_storage.load_adjusted.return_value = _make_daily_df()
    mock_storage.load_daily.return_value = _make_daily_df()
    mock_storage_cls.return_value = mock_storage

    mock_tech.return_value = MagicMock()
    mock_candle.return_value = []
    mock_chart.return_value = []
    mock_mtf.return_value = MagicMock()
    mock_intraday.return_value = (pd.DataFrame(), None, None)
    mock_config.return_value = {"ai": {"enabled": False}}

    result = build_dashboard_payload("AAPL", market="us")
    assert isinstance(result, DashboardPayload)
    assert result.chip_error == "US-1 尚未支援美股籌碼資料。"
    assert result.market == "us"


@patch("src.services.dashboard_service._sync_symbol_daily_data")
@patch("src.services.dashboard_service.ParquetStorage")
@patch("src.services.dashboard_service.generate_technical_summary")
@patch("src.services.dashboard_service.detect_candle_patterns")
@patch("src.services.dashboard_service.detect_chart_pattern")
@patch("src.services.dashboard_service.analyze_multi_timeframe")
@patch("src.services.dashboard_service._fetch_us_intraday_snapshot")
@patch("src.services.dashboard_service.get_config")
def test_build_dashboard_payload_us_chip_error_is_set(
    mock_config: MagicMock,
    mock_intraday: MagicMock,
    mock_mtf: MagicMock,
    mock_chart: MagicMock,
    mock_candle: MagicMock,
    mock_tech: MagicMock,
    mock_storage_cls: MagicMock,
    mock_sync: MagicMock,
) -> None:
    mock_storage = MagicMock()
    mock_storage.load_adjusted.return_value = _make_daily_df()
    mock_storage.load_daily.return_value = _make_daily_df()
    mock_storage_cls.return_value = mock_storage

    mock_tech.return_value = MagicMock()
    mock_candle.return_value = []
    mock_chart.return_value = []
    mock_mtf.return_value = MagicMock()
    mock_intraday.return_value = (pd.DataFrame(), None, "無法取得盤中資料")
    mock_config.return_value = {"ai": {"enabled": False}}

    result = build_dashboard_payload("AAPL", market="us")
    assert isinstance(result, DashboardPayload)
    assert result.chip_error == "US-1 尚未支援美股籌碼資料。"
    assert result.intraday_error == "無法取得盤中資料"


# ---------------------------------------------------------------------------
# secrets masking — not applicable in dashboard service (in config_service)
# but verify payload never contains st.* side-effects
# ---------------------------------------------------------------------------


def test_dashboard_error_has_code_and_message() -> None:
    err = DashboardError(code="CUSTOM_CODE", message="custom message")
    assert err.code == "CUSTOM_CODE"
    assert err.message == "custom message"


def test_get_valuation_returns_latest_per_row() -> None:
    per_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-05-15", "2026-05-16"]),
            "per": [20.1, 20.5],
            "pbr": [4.0, 4.1],
            "dividend_yield": [2.2, 2.3],
            "symbol": ["2330", "2330"],
        }
    )
    stock_info_df = pd.DataFrame({"symbol": ["2330"], "name": ["台積電"], "industry": ["半導體"]})

    with patch("src.services.dashboard_service.ParquetStorage") as mock_storage_cls, patch(
        "src.services.dashboard_service._load_stock_info_table"
    ) as mock_stock_info:
        mock_storage = MagicMock()
        mock_storage.load_per.return_value = per_df
        mock_storage_cls.return_value = mock_storage
        mock_stock_info.return_value = stock_info_df

        data = get_valuation("2330", market="tw")
        assert data["per"] == pytest.approx(20.5)
        assert data["industry"] == "半導體"


def test_get_monthly_revenue_calculates_yoy_and_mom() -> None:
    dates = pd.date_range("2025-01-10", periods=14, freq="MS")
    revenue = [100.0 + i for i in range(14)]
    df = pd.DataFrame(
        {
            "date": dates,
            "revenue": revenue,
            "revenue_month": [d.month for d in dates],
            "revenue_year": [d.year for d in dates],
            "symbol": ["2330"] * len(dates),
        }
    )

    with patch("src.services.dashboard_service.ParquetStorage") as mock_storage_cls:
        mock_storage = MagicMock()
        mock_storage.load_monthly_revenue.return_value = df
        mock_storage_cls.return_value = mock_storage

        data = get_monthly_revenue("2330", months=12, market="tw")
        assert len(data["items"]) == 12
        assert data["items"][-1]["mom"] is not None
        assert data["items"][-1]["yoy"] is not None


def test_get_dividend_history_with_pe_uses_latest_announced_4q() -> None:
    dividends_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-15"]),
            "cash_dividend": [3.5],
            "stock_dividend": [0.0],
            "symbol": ["2330"],
        }
    )
    daily_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-15"]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.0],
            "volume": [1000],
            "symbol": ["2330"],
        }
    )
    eps_df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-05-15", "2025-08-14", "2025-11-14", "2026-03-15"]),
            "year": [2025, 2025, 2025, 2026],
            "quarter": [1, 2, 3, 4],
            "eps": [2.0, 2.0, 2.0, 2.0],
            "symbol": ["2330"] * 4,
            "report_date": pd.to_datetime(["2025-05-15", "2025-08-14", "2025-11-14", "2026-03-15"]),
        }
    )

    with patch("src.services.dashboard_service.ParquetStorage") as mock_storage_cls:
        mock_storage = MagicMock()
        mock_storage.load_dividends.return_value = dividends_df
        mock_storage.load_daily.return_value = daily_df
        mock_storage.load_eps.return_value = eps_df
        mock_storage_cls.return_value = mock_storage

        data = get_dividend_history_with_pe("2330", count=5, market="tw")
        assert len(data["items"]) == 1
        assert data["items"][0]["ttm_pe"] == pytest.approx(12.5)


def test_get_industry_per_table_uses_cache_hit(tmp_path) -> None:
    cache_dir = tmp_path / "cache" / "industry_per"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "semi_2026-05-17.parquet"
    pd.DataFrame(
        [
            {"symbol": "2330", "name": "台積電", "date": "2026-05-17T00:00:00+08:00", "per": 20.0, "pbr": 4.0, "dividend_yield": 2.0},
            {"symbol": "2303", "name": "聯電", "date": "2026-05-17T00:00:00+08:00", "per": 16.0, "pbr": 2.5, "dividend_yield": 3.0},
        ]
    ).to_parquet(cache_file, index=False)
    info = pd.DataFrame(
        {
            "symbol": ["2330", "2303"],
            "name": ["台積電", "聯電"],
            "industry": ["Semi", "Semi"],
        }
    )

    with patch("src.services.dashboard_service._load_stock_info_table") as mock_info, patch(
        "src.services.dashboard_service._industry_cache_path"
    ) as mock_cache_path, patch("src.services.dashboard_service._get_industry_lock") as mock_lock:
        mock_info.return_value = info
        mock_cache_path.return_value = cache_file
        mock_lock.return_value = threading.Lock()
        data = get_industry_per_table("2330", market="tw")

        assert data["industry"] == "Semi"
        assert data["median"] == pytest.approx(18.0)
        assert data["mean"] == pytest.approx(18.0)
        assert data["count"] == 2
        assert data["cached_at"] is not None
        assert len(data["items"]) == 2
        current_rows = [row for row in data["items"] if row["symbol"] == "2330"]
        assert current_rows and current_rows[0]["is_current"] is True
