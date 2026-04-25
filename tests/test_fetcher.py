from __future__ import annotations

import os

import pandas as pd
import pytest

from src.core.config import get_config
from src.core.constants import STANDARD_COLUMNS, TAIPEI_TZ
from src.core.exceptions import FetcherError
from src.data.fetcher import FinMindFetcher, YFinanceFetcher, localize_to_taipei


def _assert_standard_columns(df: pd.DataFrame) -> None:
    assert df.columns.tolist() == STANDARD_COLUMNS


def _resolve_finmind_token() -> str:
    token = os.getenv("FINMIND_TOKEN", "").strip()
    if token:
        return token

    try:
        cfg = get_config()
    except Exception:  # noqa: BLE001 - tests should gracefully skip if config cannot be read
        return ""

    secrets = cfg.get("secrets", {}) if isinstance(cfg, dict) else {}
    if isinstance(secrets, dict):
        return str(secrets.get("finmind_token", "")).strip()
    return ""


def test_localize_naive_to_taipei() -> None:
    df = pd.DataFrame({"date": [pd.Timestamp("2026-01-01 09:00:00")]})
    localized = localize_to_taipei(df)

    assert str(localized["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"
    assert localized.loc[0, "date"].hour == 9
    assert str(localized.loc[0, "date"].tzinfo) == TAIPEI_TZ


def test_localize_utc_to_taipei() -> None:
    df = pd.DataFrame({"date": [pd.Timestamp("2026-01-01 01:00:00", tz="UTC")]})
    localized = localize_to_taipei(df)

    assert str(localized["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"
    assert localized.loc[0, "date"].hour == 9
    assert str(localized.loc[0, "date"].tzinfo) == TAIPEI_TZ


def test_empty_dataframe_has_standard_columns() -> None:
    fetcher = YFinanceFetcher(downloader=lambda *args, **kwargs: pd.DataFrame())
    result = fetcher.fetch_daily(symbol="2330", start="2025-01-01", end="2025-01-31")
    _assert_standard_columns(result)
    assert result.empty


@pytest.mark.integration
def test_finmind_daily_2330() -> None:
    token = _resolve_finmind_token()
    if not token:
        pytest.skip("FINMIND_TOKEN is not configured.")

    fetcher = FinMindFetcher(token=token)
    df = fetcher.fetch_daily(symbol="2330", start="2025-01-01", end="2025-02-01")

    assert not df.empty
    _assert_standard_columns(df)
    assert str(df["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"
    assert pd.api.types.is_float_dtype(df["close"].dtype)


@pytest.mark.integration
def test_yfinance_daily_2330() -> None:
    fetcher = YFinanceFetcher()
    df = fetcher.fetch_daily(symbol="2330", start="2025-01-01", end="2025-02-01")

    if df.empty:
        pytest.skip("yfinance returned empty data (provider/network unavailable).")

    _assert_standard_columns(df)
    assert str(df["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"


@pytest.mark.integration
def test_both_sources_same_schema() -> None:
    token = _resolve_finmind_token()
    if not token:
        pytest.skip("FINMIND_TOKEN is not configured.")

    finmind = FinMindFetcher(token=token)
    yfinance = YFinanceFetcher()

    try:
        finmind_df = finmind.fetch_daily(symbol="2330", start="2025-01-01", end="2025-02-01")
    except FetcherError as exc:
        pytest.skip(f"FinMind unavailable during integration test: {exc}")

    try:
        yfinance_df = yfinance.fetch_daily(symbol="2330", start="2025-01-01", end="2025-02-01")
    except FetcherError as exc:
        pytest.skip(f"yfinance unavailable during integration test: {exc}")

    if finmind_df.empty:
        pytest.skip("FinMind returned empty data for the selected period.")
    if yfinance_df.empty:
        pytest.skip("yfinance returned empty data (provider/network unavailable).")

    _assert_standard_columns(finmind_df)
    _assert_standard_columns(yfinance_df)
    assert [str(dt) for dt in finmind_df.dtypes] == [str(dt) for dt in yfinance_df.dtypes]


@pytest.mark.integration
def test_finmind_fetch_dividends_2330() -> None:
    token = _resolve_finmind_token()
    if not token:
        pytest.skip("FINMIND_TOKEN is not configured.")

    fetcher = FinMindFetcher(token=token)
    df = fetcher.fetch_dividends(symbol="2330", start_date="2018-01-01")
    if df.empty:
        pytest.skip("FinMind dividend endpoint returned empty data.")

    assert df.columns.tolist() == ["date", "cash_dividend", "stock_dividend", "symbol"]
    assert str(df["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"
    assert pd.api.types.is_float_dtype(df["cash_dividend"].dtype)
    assert pd.api.types.is_float_dtype(df["stock_dividend"].dtype)
