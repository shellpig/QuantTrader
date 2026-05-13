from __future__ import annotations

import os

import pandas as pd
import pytest

from src.core.config import get_config
from src.core.constants import STANDARD_COLUMNS, TAIPEI_TZ
from src.core.market import get_market_spec
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


def _build_yf_daily_df(
    dates: list[str],
    *,
    open_: list[float],
    high: list[float],
    low: list[float],
    close: list[float],
    volume: list[int],
    adj_close: list[float] | None = None,
    stock_splits: list[float] | None = None,
) -> pd.DataFrame:
    idx = pd.to_datetime(dates)
    data: dict[str, list[float] | list[int]] = {
        "Open": open_,
        "High": high,
        "Low": low,
        "Close": close,
        "Volume": volume,
    }
    if adj_close is not None:
        data["Adj Close"] = adj_close
    if stock_splits is not None:
        data["Stock Splits"] = stock_splits
    return pd.DataFrame(data, index=idx)


def test_yfinance_us_daily_uses_raw_ticker_without_tw_suffix() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        calls.append(ticker)
        return _build_yf_daily_df(
            ["2025-01-02"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[1234],
            adj_close=[100],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="us")
    fetcher.fetch_daily(symbol="AAPL", start="2025-01-01", end="2025-01-31")
    assert calls == ["AAPL"]


def test_yfinance_us_daily_normalizes_class_share_symbol() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        calls.append(ticker)
        return _build_yf_daily_df(
            ["2025-01-02"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[1234],
            adj_close=[100],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="us")
    df = fetcher.fetch_daily(symbol="BRK.B", start="2025-01-01", end="2025-01-31")
    assert calls == ["BRK-B"]
    assert df.loc[0, "symbol"] == "BRK-B"


def test_yfinance_tw_daily_keeps_tw_suffix() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        calls.append(ticker)
        return _build_yf_daily_df(
            ["2025-01-02"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[1234],
            adj_close=[100],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="tw")
    fetcher.fetch_daily(symbol="2330", start="2025-01-01", end="2025-01-31")
    assert calls == ["2330.TW"]


def test_yfinance_us_daily_normalizes_timezone_to_new_york() -> None:
    ny_tz = get_market_spec("us").timezone
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-02", "2025-01-03"],
            open_=[100, 101],
            high=[101, 102],
            low=[99, 100],
            close=[100, 101],
            volume=[1000, 1001],
            adj_close=[100, 101],
        ),
        market="us",
    )

    df = fetcher.fetch_daily(symbol="AAPL", start="2025-01-01", end="2025-01-31")
    assert str(df["date"].dtype) == f"datetime64[ns, {ny_tz}]"


def test_yfinance_us_daily_keeps_volume_as_shares() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-02"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[356650253],
            adj_close=[100],
        ),
        market="us",
    )

    df = fetcher.fetch_daily(symbol="AAPL", start="2025-01-01", end="2025-01-31")
    assert int(df.loc[0, "volume"]) == 356650253


def test_yfinance_us_adjusted_ohlc_uses_adj_close_ratio() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-02"],
            open_=[120],
            high=[130],
            low=[110],
            close=[100],
            volume=[1000],
            adj_close=[50],
            stock_splits=[0.0],
        ),
        market="us",
    )

    raw_df, adjusted_df, _, _ = fetcher.fetch_daily_with_adjusted("AAPL", "2025-01-01", "2025-01-31")
    assert not raw_df.empty
    assert adjusted_df.loc[0, "open"] == pytest.approx(60.0)
    assert adjusted_df.loc[0, "high"] == pytest.approx(65.0)
    assert adjusted_df.loc[0, "low"] == pytest.approx(55.0)
    assert adjusted_df.loc[0, "close"] == pytest.approx(50.0)


def test_yfinance_us_adjusted_volume_uses_split_factor() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-01", "2025-01-02"],
            open_=[100, 25],
            high=[101, 26],
            low=[99, 24],
            close=[100, 25],
            volume=[1000, 2000],
            adj_close=[50, 25],
            stock_splits=[0.0, 4.0],
        ),
        market="us",
    )

    _, adjusted_df, _, volume_adjusted = fetcher.fetch_daily_with_adjusted("AAPL", "2025-01-01", "2025-01-31")
    assert volume_adjusted is True
    assert int(adjusted_df.loc[0, "volume"]) == 4000
    assert int(adjusted_df.loc[1, "volume"]) == 2000


def test_yfinance_us_adjusted_volume_does_not_use_dividend_ratio() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-01", "2025-01-02"],
            open_=[100, 25],
            high=[101, 26],
            low=[99, 24],
            close=[100, 25],
            volume=[1000, 2000],
            adj_close=[90, 25],  # include dividend-like adjustment in price ratio
            stock_splits=[0.0, 4.0],
        ),
        market="us",
    )

    _, adjusted_df, _, _ = fetcher.fetch_daily_with_adjusted("AAPL", "2025-01-01", "2025-01-31")
    assert int(adjusted_df.loc[0, "volume"]) == 4000


def test_yfinance_us_adjusted_warns_when_split_factor_missing() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-01"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[1000],
            adj_close=[95],
            stock_splits=None,
        ),
        market="us",
    )

    _, adjusted_df, _, volume_adjusted = fetcher.fetch_daily_with_adjusted("AAPL", "2025-01-01", "2025-01-31")
    assert volume_adjusted is False
    assert int(adjusted_df.loc[0, "volume"]) == 1000


def test_yfinance_us_adjusted_fallback_when_adj_close_missing() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *args, **kwargs: _build_yf_daily_df(
            ["2025-01-01"],
            open_=[100],
            high=[101],
            low=[99],
            close=[100],
            volume=[1000],
            adj_close=None,
            stock_splits=[0.0],
        ),
        market="us",
    )

    raw_df, adjusted_df, _, _ = fetcher.fetch_daily_with_adjusted("AAPL", "2025-01-01", "2025-01-31")
    assert not raw_df.empty
    assert not adjusted_df.empty
    assert adjusted_df.loc[0, "close"] == pytest.approx(100.0)


def test_yfinance_us_minute_is_not_supported() -> None:
    fetcher = YFinanceFetcher(downloader=lambda *args, **kwargs: pd.DataFrame(), market="us")
    with pytest.raises(FetcherError, match="US-1 does not support US minute data"):
        fetcher.fetch_minute("AAPL", "2025-01-01", "2025-01-02", freq="1")


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
def test_yfinance_us_daily_aapl_integration() -> None:
    fetcher = YFinanceFetcher(market="us")
    try:
        df = fetcher.fetch_daily(symbol="AAPL", start="2025-01-01", end="2025-02-01")
    except FetcherError as exc:
        pytest.skip(f"yfinance unavailable during integration test: {exc}")

    if df.empty:
        pytest.skip("yfinance returned empty data (provider/network unavailable).")

    _assert_standard_columns(df)
    assert str(df["date"].dtype) == "datetime64[ns, America/New_York]"


@pytest.mark.integration
def test_yfinance_us_daily_spy_integration() -> None:
    fetcher = YFinanceFetcher(market="us")
    try:
        df = fetcher.fetch_daily(symbol="SPY", start="2025-01-01", end="2025-02-01")
    except FetcherError as exc:
        pytest.skip(f"yfinance unavailable during integration test: {exc}")

    if df.empty:
        pytest.skip("yfinance returned empty data (provider/network unavailable).")

    _assert_standard_columns(df)
    assert str(df["date"].dtype) == "datetime64[ns, America/New_York]"


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


# ---------------------------------------------------------------------------
# Phase 9-G: fetch_us_intraday tests
# ---------------------------------------------------------------------------

US_TZ = "America/New_York"


def _build_intraday_df(
    timestamps: list[str],
    *,
    open_: list[float],
    high: list[float],
    low: list[float],
    close: list[float],
    volume: list[int],
    tz: str = US_TZ,
) -> pd.DataFrame:
    idx = pd.to_datetime(timestamps).tz_localize(tz)
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close, "Volume": volume},
        index=idx,
    )


def _today_ny_ts(hour: int = 14, minute: int = 30) -> str:
    """Return a New York timestamp string for today."""
    today = pd.Timestamp.now(tz=US_TZ).date()
    return f"{today} {hour:02d}:{minute:02d}:00"


def test_yfinance_us_intraday_uses_raw_ticker_without_tw_suffix() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        calls.append(ticker)
        return _build_intraday_df(
            [_today_ny_ts(14, 30), _today_ny_ts(14, 31)],
            open_=[150.0, 151.0],
            high=[151.0, 152.0],
            low=[149.0, 150.0],
            close=[150.5, 151.5],
            volume=[10000, 11000],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="us")
    fetcher.fetch_us_intraday("TSLA")
    assert calls == ["TSLA"]


def test_yfinance_us_intraday_uses_period_1d_interval_1m_prepost_false() -> None:
    kwargs_captured: dict = {}

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        kwargs_captured.update(kwargs)
        return _build_intraday_df(
            [_today_ny_ts(14, 30)],
            open_=[150.0], high=[151.0], low=[149.0], close=[150.5], volume=[10000],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="us")
    fetcher.fetch_us_intraday("AAPL")
    assert kwargs_captured.get("period") == "1d"
    assert kwargs_captured.get("interval") == "1m"
    assert kwargs_captured.get("prepost") is False
    assert kwargs_captured.get("auto_adjust") is False


def test_yfinance_us_intraday_normalizes_timezone_to_new_york() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *a, **kw: _build_intraday_df(
            [_today_ny_ts(14, 30)],
            open_=[150.0], high=[151.0], low=[149.0], close=[150.5], volume=[10000],
        ),
        market="us",
    )
    intraday_df, snapshot, error = fetcher.fetch_us_intraday("AAPL")
    assert not intraday_df.empty
    assert str(intraday_df["date"].dtype) == f"datetime64[ns, {US_TZ}]"
    if snapshot is not None:
        assert snapshot.timestamp.tzinfo is not None
        assert "America/New_York" in str(snapshot.timestamp.tzinfo)


def test_yfinance_us_intraday_keeps_volume_as_shares() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *a, **kw: _build_intraday_df(
            [_today_ny_ts(14, 30), _today_ny_ts(14, 31)],
            open_=[150.0, 151.0], high=[151.0, 152.0], low=[149.0, 150.0],
            close=[150.5, 151.5], volume=[500000, 600000],
        ),
        market="us",
    )
    intraday_df, snapshot, _ = fetcher.fetch_us_intraday("AAPL")
    assert not intraday_df.empty
    # volume must be int shares, not lots
    total = int(intraday_df["volume"].sum())
    assert total == 1100000
    if snapshot is not None:
        assert snapshot.volume == 1100000
        assert isinstance(snapshot.volume, int)


def test_yfinance_us_intraday_empty_returns_provider_limitation() -> None:
    fetcher = YFinanceFetcher(
        downloader=lambda *a, **kw: pd.DataFrame(),
        market="us",
    )
    intraday_df, snapshot, error = fetcher.fetch_us_intraday("AAPL")
    assert snapshot is None
    assert error is not None and len(error) > 0
    # Must not raise, just return provider limitation message


def test_yfinance_us_intraday_not_today_returns_provider_limitation() -> None:
    """If the latest bar is not today's NY date, snapshot must be None."""
    fetcher = YFinanceFetcher(
        downloader=lambda *a, **kw: _build_intraday_df(
            ["2020-01-02 14:30:00"],  # old date, never today
            open_=[100.0], high=[101.0], low=[99.0], close=[100.5], volume=[10000],
        ),
        market="us",
    )
    intraday_df, snapshot, error = fetcher.fetch_us_intraday("AAPL")
    assert snapshot is None
    assert error is not None


def test_yfinance_us_intraday_raises_for_tw_market() -> None:
    fetcher = YFinanceFetcher(market="tw")
    intraday_df, snapshot, error = fetcher.fetch_us_intraday("2330")
    assert snapshot is None
    assert error is not None


def test_fetch_minute_us_still_raises_fetcher_error_after_9g() -> None:
    """9-B restriction must remain: fetch_minute(market='us') still raises FetcherError."""
    from src.core.exceptions import FetcherError
    fetcher = YFinanceFetcher(downloader=lambda *a, **kw: pd.DataFrame(), market="us")
    with pytest.raises(FetcherError, match="US-1 does not support US minute data"):
        fetcher.fetch_minute("AAPL", "2025-01-01", "2025-01-02", freq="1")


def test_yfinance_us_intraday_brk_b_normalizes_ticker() -> None:
    calls: list[str] = []

    def downloader(ticker: str, **kwargs) -> pd.DataFrame:  # noqa: ANN003
        calls.append(ticker)
        return _build_intraday_df(
            [_today_ny_ts(14, 30)],
            open_=[400.0], high=[401.0], low=[399.0], close=[400.5], volume=[50000],
        )

    fetcher = YFinanceFetcher(downloader=downloader, market="us")
    fetcher.fetch_us_intraday("BRK.B")
    assert calls == ["BRK-B"]


@pytest.mark.integration
def test_yfinance_us_intraday_tsla_integration() -> None:
    from src.data.fetcher import YFinanceFetcher
    fetcher = YFinanceFetcher(market="us")
    try:
        intraday_df, snapshot, error = fetcher.fetch_us_intraday("TSLA")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"yfinance intraday unavailable (external source): {exc}")
    assert intraday_df.columns.tolist() == STANDARD_COLUMNS or intraday_df.empty
    if not intraday_df.empty:
        assert str(intraday_df["date"].dtype) == f"datetime64[ns, {US_TZ}]"


@pytest.mark.integration
def test_yfinance_us_intraday_spy_integration() -> None:
    from src.data.fetcher import YFinanceFetcher
    fetcher = YFinanceFetcher(market="us")
    try:
        intraday_df, snapshot, error = fetcher.fetch_us_intraday("SPY")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"yfinance intraday unavailable (external source): {exc}")
    assert intraday_df.columns.tolist() == STANDARD_COLUMNS or intraday_df.empty
    if not intraday_df.empty:
        assert str(intraday_df["date"].dtype) == f"datetime64[ns, {US_TZ}]"
