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


def test_finmind_fetch_eps_normalization_prefers_basic_eps() -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "stock_id": "2330",
                        "date": "2025-05-15",
                        "type": "基本每股盈餘",
                        "value": "1.23",
                        "year": 2025,
                        "season": 1,
                    },
                    {
                        "stock_id": "2330",
                        "date": "2025-08-14",
                        "type": "稀釋每股盈餘",
                        "value": "1.49",
                        "year": 2025,
                        "season": 2,
                    },
                    {
                        "stock_id": "2330",
                        "date": "2025-08-14",
                        "type": "基本每股盈餘",
                        "value": "1.50",
                        "year": 2025,
                        "season": 2,
                    },
                    {
                        "stock_id": "2330",
                        "date": "2024-11-14",
                        "type": "EPS",
                        "value": "5.50",
                        "year": 2024,
                        "season": 4,
                    },
                ]
            }

    class DummySession:
        def get(self, *args, **kwargs) -> DummyResponse:  # noqa: ANN002, ANN003
            return DummyResponse()

    fetcher = FinMindFetcher(token="dummy-token", session=DummySession())
    eps_df = fetcher.fetch_eps(symbol="2330", start_date="2024-01-01")

    assert eps_df.columns.tolist() == ["year", "quarter", "eps", "symbol", "report_date"]
    assert list(zip(eps_df["year"], eps_df["quarter"], strict=True)) == [(2024, 4), (2025, 1), (2025, 2)]
    assert eps_df.loc[(eps_df["year"] == 2025) & (eps_df["quarter"] == 2), "eps"].iloc[0] == pytest.approx(1.50)
    assert TAIPEI_TZ in str(eps_df["report_date"].dtype)


def test_finmind_fetch_splits_normalizes_schema() -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "date": "2025-06-18",
                        "before_price": "188.65",
                        "after_price": "47.16",
                        "stock_id": "0050",
                        "open_price": "47.16",
                    }
                ]
            }

    class DummySession:
        def get(self, *args, **kwargs) -> DummyResponse:  # noqa: ANN002, ANN003
            return DummyResponse()

    fetcher = FinMindFetcher(token="dummy-token", session=DummySession())
    split_df = fetcher.fetch_splits(symbol="0050", start_date="2025-01-01")

    assert split_df.columns.tolist() == ["date", "before_price", "after_price", "symbol"]
    assert len(split_df) == 1
    assert split_df.loc[0, "symbol"] == "0050"
    assert split_df.loc[0, "before_price"] == pytest.approx(188.65)
    assert split_df.loc[0, "after_price"] == pytest.approx(47.16)
    assert str(split_df["date"].dtype) == f"datetime64[ns, {TAIPEI_TZ}]"


def test_finmind_fetch_stock_info_normalizes_schema() -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {
                        "stock_id": "2330",
                        "stock_name": "台積電",
                        "type": "twse",
                        "industry_category": "半導體",
                    }
                ]
            }

    class DummySession:
        def get(self, *args, **kwargs) -> DummyResponse:  # noqa: ANN002, ANN003
            return DummyResponse()

    fetcher = FinMindFetcher(token="dummy-token", session=DummySession())
    info = fetcher.fetch_stock_info()

    assert info.columns.tolist() == ["symbol", "name", "type", "industry"]
    assert info.iloc[0].to_dict() == {
        "symbol": "2330",
        "name": "台積電",
        "type": "twse",
        "industry": "半導體",
    }


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
