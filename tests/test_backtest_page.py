from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from src.core.constants import TAIPEI_TZ
from src.core.exceptions import FetcherError
from src.core.market import get_market_spec
from src.ui.pages.backtest import (
    DcaBacktestResult,
    _TW_SYMBOL_PATTERN,
    _build_eps_display_table,
    _build_price_features,
    _candlestick_colors,
    _dca_transactions_to_trade_markers,
    _extract_trade_markers,
    _load_backtest_data,
    _nearest_trading_indices,
    _price_panel_caption,
    _render_dca_summary,
    _render_dca_transactions,
    _run_backtest,
)


def test_nearest_trading_indices_prefers_future_on_tie() -> None:
    trading = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-01-03", tz=TAIPEI_TZ),
            pd.Timestamp("2026-01-05", tz=TAIPEI_TZ),
        ]
    )
    targets = pd.DatetimeIndex([pd.Timestamp("2026-01-04", tz=TAIPEI_TZ)])

    nearest = _nearest_trading_indices(targets, trading)

    assert nearest.tolist() == [1]


def test_build_price_features_rolling_mean_matches_expected() -> None:
    price_df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=6, freq="D", tz=TAIPEI_TZ),
            "close": [1, 2, 3, 4, 5, 6],
        }
    )

    out = _build_price_features(price_df)

    assert pd.isna(out.loc[3, "ma5"])
    assert out.loc[4, "ma5"] == 3.0
    assert out.loc[5, "ma5"] == 4.0
    assert out["ma20"].isna().all()
    assert out["ma60"].isna().all()


def test_backtest_symbol_pattern_accepts_alphanumeric_etf_code() -> None:
    assert _TW_SYMBOL_PATTERN.fullmatch("00981A")


def test_build_eps_display_table_partial_latest_year_no_estimation() -> None:
    eps_df = pd.DataFrame(
        {
            "year": [2025, 2025, 2024, 2024, 2024, 2024],
            "quarter": [1, 2, 1, 2, 3, 4],
            "eps": [1.2, 1.5, 0.5, 0.5, 0.5, 0.5],
        }
    )

    display = _build_eps_display_table(eps_df=eps_df, end_year=2025)

    assert not display.empty
    assert display.iloc[0]["年度"] == 2025
    assert display.iloc[0]["Q1 EPS"] == "1.20"
    assert display.iloc[0]["Q2 EPS"] == "1.50"
    assert display.iloc[0]["Q3 EPS"] == "尚無資料"
    assert display.iloc[0]["Q4 EPS"] == "尚無資料"
    assert display.iloc[0]["年度 EPS"] == "2.70"
    assert display.iloc[1]["年度"] == 2024
    assert display.iloc[1]["年度 EPS"] == "2.00"


def test_extract_trade_markers_preserves_quantity() -> None:
    trades = pd.DataFrame(
        {
            "entry_date": [pd.Timestamp("2026-01-02", tz=TAIPEI_TZ)],
            "exit_date": [pd.Timestamp("2026-01-06", tz=TAIPEI_TZ)],
            "entry_price": [100.0],
            "exit_price": [110.0],
            "quantity": [3000],
        }
    )

    buy_marks, sell_marks = _extract_trade_markers(trades=trades)

    assert buy_marks.iloc[0]["quantity"] == 3000
    assert sell_marks.iloc[0]["quantity"] == 3000


def test_dca_transactions_to_trade_markers_only_keeps_filled_rows() -> None:
    tx = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-02-05", "2026-03-05"], utc=True),
            "status": ["FILLED", "SKIPPED"],
            "buy_price": [100.0, 101.0],
            "buy_shares": [10, 0],
        }
    )

    trades = _dca_transactions_to_trade_markers(tx)
    buy_marks, sell_marks = _extract_trade_markers(trades=trades)

    assert len(buy_marks) == 1
    assert buy_marks.iloc[0]["quantity"] == 10
    assert sell_marks.empty


def test_load_backtest_data_raises_when_adjusted_missing(monkeypatch) -> None:
    class StubStorage:
        def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"])

        def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"])

    monkeypatch.setattr("src.ui.pages.backtest.ParquetStorage", lambda: StubStorage())
    monkeypatch.setattr("src.ui.pages.backtest._sync_symbol_daily_data", lambda symbol, storage, market="tw": None)

    with pytest.raises(FetcherError, match="adjusted data is missing"):
        _load_backtest_data(
            symbol="0050",
            start_ts=pd.Timestamp("2025-01-01", tz=TAIPEI_TZ),
            end_exclusive=pd.Timestamp("2025-12-31", tz=TAIPEI_TZ),
            require_adjusted=True,
        )


def test_load_backtest_data_allows_daily_fallback_when_disabled(monkeypatch) -> None:
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03"]).tz_localize(TAIPEI_TZ),
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000, 1000],
            "symbol": ["0050", "0050"],
        }
    )

    class StubStorage:
        def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return pd.DataFrame(columns=daily.columns)

        def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return daily.copy(deep=True)

    monkeypatch.setattr("src.ui.pages.backtest.ParquetStorage", lambda: StubStorage())
    monkeypatch.setattr("src.ui.pages.backtest._sync_symbol_daily_data", lambda symbol, storage, market="tw": None)

    out = _load_backtest_data(
        symbol="0050",
        start_ts=pd.Timestamp("2025-01-01", tz=TAIPEI_TZ),
        end_exclusive=pd.Timestamp("2025-01-10", tz=TAIPEI_TZ),
        require_adjusted=False,
    )

    assert len(out) == 2


def test_load_backtest_data_runs_auto_sync_before_loading(monkeypatch) -> None:
    called: dict[str, str] = {}
    daily = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02"]).tz_localize(TAIPEI_TZ),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
            "symbol": ["0050"],
        }
    )

    class StubStorage:
        def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return daily.copy(deep=True)

        def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return daily.copy(deep=True)

    monkeypatch.setattr("src.ui.pages.backtest.ParquetStorage", lambda: StubStorage())

    def _mark_sync(symbol: str, storage, market: str = "tw") -> None:  # noqa: ANN001
        called["symbol"] = symbol

    monkeypatch.setattr("src.ui.pages.backtest._sync_symbol_daily_data", _mark_sync)

    _load_backtest_data(
        symbol="0050",
        start_ts=pd.Timestamp("2025-01-01", tz=TAIPEI_TZ),
        end_exclusive=pd.Timestamp("2025-01-10", tz=TAIPEI_TZ),
        require_adjusted=True,
    )

    assert called["symbol"] == "0050"


def test_sync_symbol_daily_data_fallback_when_primary_update_fails(monkeypatch) -> None:
    import src.ui.pages.backtest as backtest_module

    calls: list[str] = []

    class _Fetcher:
        def __init__(self, source: str):
            self.source = source

    class _Maintenance:
        def __init__(self, *, fetcher, **kwargs):  # noqa: ANN003
            self.fetcher = fetcher

        def update_daily(self, symbol: str, market: str = "tw") -> None:
            calls.append(f"{self.fetcher.source}:{symbol}")
            if self.fetcher.source == "finmind":
                raise RuntimeError("primary update failed")

    class _Meta:
        def close(self) -> None:
            return None

    monkeypatch.setattr(backtest_module, "DuckDBMeta", _Meta)
    monkeypatch.setattr(backtest_module, "DataMaintenance", _Maintenance)
    monkeypatch.setattr(
        backtest_module,
        "_build_fetchers_from_config",
        lambda market="tw": [("finmind", _Fetcher("finmind")), ("yfinance", _Fetcher("yfinance"))],
    )

    backtest_module._sync_symbol_daily_data("2330", storage=object())  # type: ignore[arg-type]

    assert calls == ["finmind:2330", "yfinance:2330"]


def test_load_backtest_data_uses_us_adjusted_path_by_default(monkeypatch) -> None:
    ny_tz = get_market_spec("us").timezone
    called: dict[str, str] = {}
    adjusted = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03"]).tz_localize(ny_tz),
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000, 1100],
            "symbol": ["AAPL", "AAPL"],
        }
    )

    class StubStorage:
        def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:
            called["symbol"] = symbol
            called["market"] = market
            return adjusted.copy(deep=True)

        def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return pd.DataFrame(columns=adjusted.columns)

    monkeypatch.setattr("src.ui.pages.backtest.ParquetStorage", lambda: StubStorage())
    monkeypatch.setattr("src.ui.pages.backtest._sync_symbol_daily_data", lambda symbol, storage, market="tw": None)

    out = _load_backtest_data(
        symbol="AAPL",
        start_ts=pd.Timestamp("2025-01-01", tz=ny_tz),
        end_exclusive=pd.Timestamp("2025-01-10", tz=ny_tz),
        require_adjusted=True,
        market="us",
    )

    assert called == {"symbol": "AAPL", "market": "us"}
    assert len(out) == 2
    assert str(out["date"].dt.tz) == ny_tz


def test_load_backtest_data_runs_auto_sync_with_us_market(monkeypatch) -> None:
    ny_tz = get_market_spec("us").timezone
    called: dict[str, str] = {}
    adjusted = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02"]).tz_localize(ny_tz),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
            "symbol": ["AAPL"],
        }
    )

    class StubStorage:
        def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return adjusted.copy(deep=True)

        def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:  # noqa: ARG002
            return adjusted.copy(deep=True)

    monkeypatch.setattr("src.ui.pages.backtest.ParquetStorage", lambda: StubStorage())

    def _mark_sync(symbol: str, storage, market: str = "tw") -> None:  # noqa: ANN001
        called["symbol"] = symbol
        called["market"] = market

    monkeypatch.setattr("src.ui.pages.backtest._sync_symbol_daily_data", _mark_sync)

    _load_backtest_data(
        symbol="AAPL",
        start_ts=pd.Timestamp("2025-01-01", tz=ny_tz),
        end_exclusive=pd.Timestamp("2025-01-10", tz=ny_tz),
        require_adjusted=True,
        market="us",
    )

    assert called == {"symbol": "AAPL", "market": "us"}


def test_us_backtest_displays_usd_currency(monkeypatch) -> None:
    import src.ui.pages.backtest as backtest_module

    captions: list[str] = []

    class _DummyCol:
        def metric(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
            return None

    class _DummyReport:
        def get_streamlit_figures(self) -> dict[str, object]:
            return {"equity": object(), "drawdown": object(), "monthly": object(), "summary": object()}

    monkeypatch.setattr(backtest_module, "TearsheetReport", lambda result: _DummyReport())
    monkeypatch.setattr(backtest_module.st, "columns", lambda n: [_DummyCol() for _ in range(n)])
    monkeypatch.setattr(backtest_module.st, "caption", lambda text: captions.append(str(text)))
    monkeypatch.setattr(backtest_module.st, "plotly_chart", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module, "get_config", lambda: {"ui": {"use_extras": False}})

    result = SimpleNamespace(
        total_trades=3,
        total_return=0.1,
        annual_return=0.08,
        max_drawdown=0.2,
        sharpe_ratio=1.2,
    )
    backtest_module._render_tearsheet_metrics(result, market="us")

    assert any("幣別：USD" in text for text in captions)


def test_us_dca_warns_fractional_shares_not_supported(monkeypatch) -> None:
    import src.ui.pages.backtest as backtest_module

    warnings: list[str] = []
    ny_tz = get_market_spec("us").timezone
    sample = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-03"]).tz_localize(ny_tz),
            "open": [100.0, 101.0],
            "high": [101.0, 102.0],
            "low": [99.0, 100.0],
            "close": [100.5, 101.5],
            "volume": [1000, 1000],
            "symbol": ["AAPL", "AAPL"],
        }
    )

    monkeypatch.setattr(backtest_module, "_load_backtest_data", lambda **kwargs: sample.copy(deep=True))
    monkeypatch.setattr(
        backtest_module,
        "run_dca_backtest",
        lambda **kwargs: DcaBacktestResult(
            transactions=pd.DataFrame(
                columns=[
                    "date",
                    "status",
                    "reason",
                    "invested_amount",
                    "buy_price",
                    "buy_shares",
                    "commission",
                    "spend",
                    "cash_balance",
                    "cumulative_shares",
                    "cumulative_invested",
                    "average_cost",
                ]
            ),
            cumulative_invested=0.0,
            market_value=0.0,
            cash_balance=0.0,
            unrealized_pnl=0.0,
            total_return_rate=0.0,
            cumulative_shares=0,
            average_cost=0.0,
            contribution_count=0,
        ),
    )
    monkeypatch.setattr(backtest_module, "_render_dca_summary", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module, "_render_dca_transactions", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module, "_render_price_and_indicator_panel", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.st, "warning", lambda text: warnings.append(str(text)))
    monkeypatch.setattr(backtest_module.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.st, "error", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.st, "divider", lambda: None)

    _run_backtest(
        symbol="AAPL",
        start_date=pd.Timestamp("2025-01-01"),
        end_date=pd.Timestamp("2025-01-10"),
        engine_name="向量化引擎",
        strategy_preset={"type": "dollar_cost_averaging", "params": {}},
        market="us",
    )

    assert any("不支援碎股" in text for text in warnings)


def test_us_backtest_does_not_display_lot_unit(monkeypatch) -> None:
    import src.ui.pages.backtest as backtest_module

    metric_labels: list[str] = []
    table_columns: list[str] = []

    class _DummyCol:
        def metric(self, label: str, value: str) -> None:  # noqa: ARG002
            metric_labels.append(label)

    monkeypatch.setattr(backtest_module.st, "columns", lambda n: [_DummyCol() for _ in range(n)])
    monkeypatch.setattr(backtest_module.st, "subheader", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.st, "info", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module.st, "caption", lambda *args, **kwargs: None)
    monkeypatch.setattr(backtest_module, "get_config", lambda: {"ui": {"use_extras": False}})

    def _capture_df(df: pd.DataFrame, **kwargs) -> None:  # noqa: ANN003, ARG001
        table_columns.extend([str(col) for col in df.columns])

    monkeypatch.setattr(backtest_module.st, "dataframe", _capture_df)

    summary = DcaBacktestResult(
        transactions=pd.DataFrame(),
        cumulative_invested=1000.0,
        market_value=950.0,
        cash_balance=50.0,
        unrealized_pnl=-50.0,
        total_return_rate=-0.05,
        cumulative_shares=3,
        average_cost=333.3333,
        contribution_count=1,
    )
    _render_dca_summary(summary, market="us")

    tx = pd.DataFrame(
        {
            "date": [pd.Timestamp("2025-01-15")],
            "status": ["FILLED"],
            "reason": [""],
            "invested_amount": [1000.0],
            "buy_price": [300.0],
            "buy_shares": [3],
            "commission": [0.0],
            "spend": [900.0],
            "cash_balance": [100.0],
            "cumulative_shares": [3],
            "cumulative_invested": [1000.0],
            "average_cost": [300.0],
        }
    )
    _render_dca_transactions(tx, market="us")

    assert all("張" not in label for label in metric_labels)
    assert all("張" not in column for column in table_columns)


def test_price_panel_caption_is_market_aware() -> None:
    assert "台股慣例" in _price_panel_caption("tw")
    assert "台股慣例" not in _price_panel_caption("us")


def test_candlestick_colors_market_aware() -> None:
    tw = _candlestick_colors("tw")
    us = _candlestick_colors("us")
    assert tw == {"increasing": "#d62728", "decreasing": "#2ca02c"}
    assert us == {"increasing": "#2ca02c", "decreasing": "#d62728"}
