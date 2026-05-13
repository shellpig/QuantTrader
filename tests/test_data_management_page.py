from __future__ import annotations

import pandas as pd

from src.ui.pages.data_management import (
    _build_fetchers_from_config,
    _render_market_capabilities,
    _render_meta_table,
    _render_optional_us_status,
    _render_us_data_status,
    _run_maintenance,
)


class _StubProgress:
    def progress(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None


class _StubSt:
    def __init__(self) -> None:
        self.captions: list[str] = []
        self.infos: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.dataframes: list[pd.DataFrame] = []

    def caption(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.captions.append(str(message))

    def info(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.infos.append(str(message))

    def error(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.errors.append(str(message))

    def success(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.successes.append(str(message))

    def progress(self, *args, **kwargs) -> _StubProgress:  # noqa: ANN002, ANN003
        return _StubProgress()

    def json(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def dataframe(self, data, *args, **kwargs) -> None:  # noqa: ANN001, ANN002, ANN003
        self.dataframes.append(data.copy(deep=True))


def test_data_management_us_mode_shows_disabled_messages(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    stub = _StubSt()
    monkeypatch.setattr(module, "st", stub)

    _render_market_capabilities("us")

    assert any("僅支援日 K 更新與重建" in msg for msg in stub.captions)
    assert "US-1 尚未支援美股分 K。" in stub.infos
    assert "US-1 尚未支援美股籌碼資料。" in stub.infos


def test_data_management_us_update_calls_market_us(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    captured: dict[str, str] = {}
    stub = _StubSt()

    class _Fetcher:
        pass

    class _Meta:
        def close(self) -> None:
            return None

    class _Maintenance:
        def __init__(self, *, fetcher, storage, meta, cleaner):  # noqa: ANN001
            return None

        def update_daily(self, symbol: str, market: str = "tw") -> int:
            captured["symbol"] = symbol
            captured["market"] = market
            return 3

    monkeypatch.setattr(module, "st", stub)
    monkeypatch.setattr(module, "_build_fetchers_from_config", lambda market="tw": [("yfinance", _Fetcher())])
    monkeypatch.setattr(module, "ParquetStorage", lambda: object())
    monkeypatch.setattr(module, "DuckDBMeta", _Meta)
    monkeypatch.setattr(module, "DataCleaner", lambda: object())
    monkeypatch.setattr(module, "DataMaintenance", _Maintenance)

    _run_maintenance(symbol="BRK-B", rebuild=False, market="us")

    assert captured == {"symbol": "BRK-B", "market": "us"}
    assert any("BRK-B 更新完成" in msg for msg in stub.successes)
    assert not stub.errors


def test_data_management_us_fetcher_source_forced_yfinance(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    class _YF:
        def __init__(self, market: str = "tw"):
            self.market = market

    monkeypatch.setattr(module, "get_config", lambda: {"data": {"primary_source": "finmind", "fallback_source": "finmind"}})
    monkeypatch.setattr(module, "YFinanceFetcher", _YF)

    fetchers = _build_fetchers_from_config(market="us")

    assert len(fetchers) == 1
    assert fetchers[0][0] == "yfinance"
    assert fetchers[0][1].market == "us"


def test_render_meta_table_filters_by_market(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    stub = _StubSt()

    class _Meta:
        def list_all(self) -> pd.DataFrame:
            return pd.DataFrame(
                [
                    {"market": "tw", "symbol": "2330", "freq": "daily", "source": "finmind", "row_count": 10},
                    {"market": "us", "symbol": "AAPL", "freq": "daily", "source": "yfinance", "row_count": 20},
                ]
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(module, "st", stub)
    monkeypatch.setattr(module, "DuckDBMeta", _Meta)

    _render_meta_table(market="us")

    assert len(stub.dataframes) == 1
    assert set(stub.dataframes[0]["market"]) == {"us"}
    assert set(stub.dataframes[0]["symbol"]) == {"AAPL"}


def test_data_management_us_status_shows_raw_and_adjusted(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    stub = _StubSt()
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02", "2025-01-05"]),
            "open": [1.0, 2.0],
            "high": [1.0, 2.0],
            "low": [1.0, 2.0],
            "close": [1.0, 2.0],
            "volume": [100, 200],
            "symbol": ["AAPL", "AAPL"],
        }
    )
    adjusted = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-03", "2025-01-07"]),
            "open": [1.0, 2.0],
            "high": [1.0, 2.0],
            "low": [1.0, 2.0],
            "close": [1.0, 2.0],
            "volume": [100, 200],
            "symbol": ["AAPL", "AAPL"],
        }
    )

    class _Storage:
        def load_daily(self, symbol: str, market: str = "us") -> pd.DataFrame:
            return raw.copy(deep=True)

        def load_adjusted(self, symbol: str, market: str = "us") -> pd.DataFrame:
            return adjusted.copy(deep=True)

    monkeypatch.setattr(module, "st", stub)
    _render_us_data_status("AAPL", _Storage())  # type: ignore[arg-type]

    status_df = stub.dataframes[0]
    assert list(status_df["資料類型"]) == ["raw daily", "adjusted daily"]
    assert list(status_df["狀態"]) == ["可用", "可用"]
    assert list(status_df["筆數"]) == [2, 2]
    assert list(status_df["起始日"]) == ["2025-01-02", "2025-01-03"]
    assert list(status_df["結束日"]) == ["2025-01-05", "2025-01-07"]


def test_data_management_us_status_handles_missing_adjusted(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    stub = _StubSt()
    raw = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-01-02"]),
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
            "close": [1.0],
            "volume": [100],
            "symbol": ["AAPL"],
        }
    )
    empty = pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"])

    class _Storage:
        def load_daily(self, symbol: str, market: str = "us") -> pd.DataFrame:
            return raw.copy(deep=True)

        def load_adjusted(self, symbol: str, market: str = "us") -> pd.DataFrame:
            return empty.copy(deep=True)

    monkeypatch.setattr(module, "st", stub)
    _render_us_data_status("AAPL", _Storage())  # type: ignore[arg-type]

    status_df = stub.dataframes[0]
    adjusted_row = status_df.loc[status_df["資料類型"] == "adjusted daily"].iloc[0]
    assert adjusted_row["狀態"] == "尚無資料"
    assert adjusted_row["筆數"] == 0
    assert adjusted_row["起始日"] == "-"
    assert adjusted_row["結束日"] == "-"


def test_data_management_tw_does_not_show_us_status(monkeypatch) -> None:
    import src.ui.pages.data_management as module

    called = {"us_status": False}
    monkeypatch.setattr(module, "_render_us_data_status", lambda symbol, storage: called.__setitem__("us_status", True))

    _render_optional_us_status(market="tw", symbol="2330")

    assert not called["us_status"]
