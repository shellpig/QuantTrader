from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.analysis.technical_summary import PriceLevel, TechnicalSummary
from src.analysis.pattern import MultiTimeframeAnalysis, TimeframeTrend
from src.data.storage import ParquetStorage
from src.data.realtime import BidAskStructure, RealtimeQuote
from src.ui.pages.dashboard import (
    _build_recent_institutional_table,
    _build_dashboard_payload,
    _prepare_chip_data_for_dashboard,
    _render_tab_ai,
    _render_tab_chip,
    _render_tab_overview,
    _style_recent_institutional_table,
    render_dashboard_page,
)


class _DummyCtx:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False

    def metric(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def write(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def caption(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None


class _DummySt:
    def __init__(self, *, symbol: str = "", analyze_clicked: bool = False, button_map: dict[str, bool] | None = None):
        self._symbol = symbol
        self._analyze_clicked = analyze_clicked
        self._button_map = button_map or {}
        self.session_state: dict[str, object] = {}
        self.info_messages: list[str] = []
        self.warning_messages: list[str] = []
        self.caption_messages: list[str] = []
        self.tabs_called_count = 0
        self.rerun_called_count = 0

    def title(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def caption(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        if args:
            self.caption_messages.append(str(args[0]))
        return None

    def text_input(self, *args, **kwargs) -> str:  # noqa: ANN002, ANN003
        return self._symbol

    def button(self, *args, **kwargs) -> bool:  # noqa: ANN002, ANN003
        key = str(kwargs.get("key", ""))
        if key in self._button_map:
            return bool(self._button_map[key])
        return self._analyze_clicked

    def selectbox(self, *args, **kwargs):  # noqa: ANN002, ANN003
        options = kwargs.get("options")
        index = int(kwargs.get("index", 0))
        if isinstance(options, (list, tuple)) and options:
            return options[index]
        return None

    def info(self, message: str, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        self.info_messages.append(message)

    def warning(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        if args:
            self.warning_messages.append(str(args[0]))
        return None

    def subheader(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def columns(self, n: int | list[int], *args, **kwargs):  # noqa: ANN002, ANN003
        if isinstance(n, list):
            count = len(n)
        else:
            count = int(n)
        return [_DummyCtx() for _ in range(count)]

    def markdown(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def write(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def metric(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def progress(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def dataframe(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def success(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def tabs(self, labels):  # noqa: ANN001
        self.tabs_called_count += 1
        return [_DummyCtx() for _ in labels]

    def plotly_chart(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        return None

    def rerun(self) -> None:
        self.rerun_called_count += 1


class _MetricCaptureCtx(_DummyCtx):
    def __init__(self, sink: list[tuple[str, str]]):
        self._sink = sink

    def metric(self, label, value, *args, **kwargs) -> None:  # noqa: ANN001, ANN002, ANN003
        self._sink.append((str(label), str(value)))


class _MetricCaptureSt(_DummySt):
    def __init__(self, **kwargs):  # noqa: ANN003
        super().__init__(**kwargs)
        self.metrics: list[tuple[str, str]] = []

    def columns(self, n: int | list[int], *args, **kwargs):  # noqa: ANN002, ANN003
        if isinstance(n, list):
            count = len(n)
        else:
            count = int(n)
        return [_MetricCaptureCtx(self.metrics) for _ in range(count)]


def _make_technical_summary() -> TechnicalSummary:
    return TechnicalSummary(
        trend_direction="多頭趨勢",
        ma_status="多頭排列 (5>20>60)",
        kd_status="KD 多方",
        macd_status="正值擴張",
        volume_status="量能正常",
        volume_price_relation="量價同步",
        short_term_score=0.66,
        short_term_label="中等偏多",
        short_term_components={"ma": 0.7, "kd": 0.6, "volume_price": 0.6, "breakout": 0.7},
        resistance_levels=[PriceLevel(value=110.0, label="近20日高點", kind="resistance")],
        support_levels=[PriceLevel(value=100.0, label="MA20", kind="support")],
        volume_price_divergence="量價同步",
        ma_bias="與 MA20 乖離約 +1.20%，中性",
        chip_behavior="法人偏多",
        operation_observation="偏多但留意波動",
    )


def _make_daily_df(periods: int = 90) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.date_range("2025-01-01", periods=periods, freq="D"),
            "open": [100.0 + i for i in range(periods)],
            "high": [101.0 + i for i in range(periods)],
            "low": [99.0 + i for i in range(periods)],
            "close": [100.5 + i for i in range(periods)],
            "volume": [1000 + i for i in range(periods)],
            "symbol": ["2330"] * periods,
        }
    )


def test_dashboard_page_imports() -> None:
    from src.ui.pages.dashboard import render_dashboard_page as imported  # noqa: PLC0415

    assert callable(imported)


def test_dashboard_page_render_no_symbol(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _DummySt(symbol="", analyze_clicked=False)
    monkeypatch.setattr(dashboard_module, "st", dummy)
    render_dashboard_page()
    assert any("請先輸入股票代碼" in msg for msg in dummy.info_messages)


def test_dashboard_page_accepts_alphanumeric_symbol(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _DummySt(symbol="00981a", analyze_clicked=True)
    monkeypatch.setattr(dashboard_module, "st", dummy)
    monkeypatch.setattr(
        dashboard_module,
        "_build_dashboard_payload",
        lambda symbol: {"symbol": symbol, "ready": False, "error": f"{symbol} 尚無本機日線資料"},
    )

    render_dashboard_page()

    assert not dummy.info_messages
    assert any("00981A 尚無本機日線資料" in msg for msg in dummy.warning_messages)


def test_dashboard_tab_overview_renders(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    monkeypatch.setattr(dashboard_module, "st", _DummySt())
    _render_tab_overview(
        quote=None,
        technical=_make_technical_summary(),
        df=pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"]),
    )


def test_dashboard_tab_overview_intraday_uses_bid_ask_not_mid_estimate(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _MetricCaptureSt()
    monkeypatch.setattr(dashboard_module, "st", dummy)
    quote = RealtimeQuote(
        symbol="3293",
        name="鈊象",
        price=731.5,
        change=-35.0,
        change_pct=-1.53,
        open=725.0,
        high=740.0,
        low=720.0,
        yesterday_close=2287.5,
        volume=1234,
        timestamp="10:05:00",
        best_bid=[2255.0],
        best_ask=[2260.0],
        is_market_open=True,
        is_estimated_price=True,
        price_label="委買賣估算價",
    )
    _render_tab_overview(
        quote=quote,
        technical=_make_technical_summary(),
        df=pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"]),
    )

    labels = [label for label, _ in dummy.metrics]
    metric_map = dict(dummy.metrics)
    values = [value for _, value in dummy.metrics]
    assert "買一" in labels
    assert "賣一" in labels
    assert "即時價" not in labels
    assert "731.50" not in values
    assert metric_map.get("漲跌") == "-32.50"
    assert metric_map.get("漲跌幅") == "-1.42%"


def test_dashboard_tab_overview_after_hours_uses_latest_daily_close_and_volume(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _MetricCaptureSt()
    monkeypatch.setattr(dashboard_module, "st", dummy)
    quote = RealtimeQuote(
        symbol="2330",
        name="台積電",
        price=999.0,
        change=0.0,
        change_pct=0.0,
        open=0.0,
        high=0.0,
        low=0.0,
        yesterday_close=120.0,
        volume=1,
        timestamp="14:00:00",
        is_market_open=False,
    )
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-05-09", "2026-05-10"]),
            "open": [120.0, 121.0],
            "high": [121.0, 123.0],
            "low": [119.0, 120.5],
            "close": [121.5, 122.0],
            "volume": [9000, 9876],
            "symbol": ["2330", "2330"],
        }
    )
    _render_tab_overview(quote=quote, technical=_make_technical_summary(), df=df)

    metric_map = dict(dummy.metrics)
    assert metric_map.get("收盤價") == "122.00"
    assert metric_map.get("日成交量(張)") == "9,876"


def test_dashboard_tab_chip_no_data(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _DummySt()
    monkeypatch.setattr(dashboard_module, "st", dummy)
    _render_tab_chip(chip=None, bid_ask=None, technical=_make_technical_summary())
    assert any("尚未載入籌碼資料" in msg for msg in dummy.info_messages)


def test_dashboard_tab_ai_disabled(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _DummySt()
    monkeypatch.setattr(dashboard_module, "st", dummy)
    _render_tab_ai(analysis=None, technical=_make_technical_summary(), ai_enabled=False)
    assert any("請啟用 AI 功能" in msg for msg in dummy.info_messages)


def test_dashboard_option_menu_entry() -> None:
    app_path = Path("src/ui/app.py")
    source = app_path.read_text(encoding="utf-8")
    assert "個股分析" in source


def test_dashboard_page_not_ready_payload_does_not_render_tabs(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    dummy = _DummySt(symbol="2330", analyze_clicked=True)
    monkeypatch.setattr(dashboard_module, "st", dummy)
    monkeypatch.setattr(
        dashboard_module,
        "_build_dashboard_payload",
        lambda symbol: {"symbol": symbol, "ready": False, "error": "尚無本機日線資料"},
    )

    render_dashboard_page()

    assert dummy.tabs_called_count == 0
    assert any("尚無本機日線資料" in msg for msg in dummy.warning_messages)


def test_dashboard_page_refresh_quote_updates_session_payload(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    technical = _make_technical_summary()
    old_quote = RealtimeQuote(
        symbol="2330",
        name="台積電",
        price=100.0,
        change=0.0,
        change_pct=0.0,
        open=100.0,
        high=101.0,
        low=99.0,
        yesterday_close=100.0,
        volume=1000,
        timestamp="10:00:00",
    )
    payload = {
        "symbol": "2330",
        "ready": True,
        "error": None,
        "daily_df": pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "symbol"]),
        "technical": technical,
        "quote": old_quote,
        "bid_ask": None,
        "chip": None,
        "candle_patterns": [],
        "chart_patterns": [],
        "multi_timeframe": MultiTimeframeAnalysis(
            daily=TimeframeTrend(timeframe="daily", trend_direction="盤整", strength="中"),
            weekly=TimeframeTrend(timeframe="weekly", trend_direction="盤整", strength="中"),
            monthly=TimeframeTrend(timeframe="monthly", trend_direction="盤整", strength="中"),
        ),
        "analysis": None,
        "ai_enabled": False,
    }

    dummy = _DummySt(
        symbol="2330",
        analyze_clicked=False,
        button_map={"dashboard_refresh_quote": True},
    )
    dummy.session_state["dashboard_payload"] = payload
    monkeypatch.setattr(dashboard_module, "st", dummy)

    new_quote = RealtimeQuote(
        symbol="2330",
        name="台積電",
        price=123.45,
        change=1.0,
        change_pct=0.8,
        open=122.0,
        high=124.0,
        low=121.0,
        yesterday_close=122.45,
        volume=2000,
        timestamp="10:05:00",
    )
    new_bid_ask = BidAskStructure(
        total_bid_vol=500,
        total_ask_vol=400,
        bid_ratio=0.56,
        ask_ratio=0.44,
        label="買盤較積極",
    )
    monkeypatch.setattr(
        dashboard_module,
        "_refresh_realtime_snapshot",
        lambda symbol: (new_quote, new_bid_ask, None),
    )

    render_dashboard_page()

    updated = dummy.session_state["dashboard_payload"]
    assert updated["quote"].price == 123.45
    assert updated["bid_ask"].label == "買盤較積極"
    assert dummy.rerun_called_count == 1


def test_dashboard_payload_builds_multi_timeframe_from_date_column(monkeypatch, tmp_path) -> None:
    import src.ui.pages.dashboard as dashboard_module

    storage = ParquetStorage(data_dir=tmp_path)
    storage.save_daily("2330", _make_daily_df())
    monkeypatch.setattr(dashboard_module, "ParquetStorage", lambda: storage)
    monkeypatch.setattr(dashboard_module, "RealtimeFetcher", None)
    monkeypatch.setattr(dashboard_module, "st", _DummySt())
    monkeypatch.setattr(dashboard_module, "get_config", lambda: {"ai": {"enabled": False}, "ui": {"theme": "midnight_blue"}})
    monkeypatch.setattr(
        dashboard_module,
        "_prepare_daily_data_for_dashboard",
        lambda symbol, storage: (storage.load_daily(symbol), None),
    )
    monkeypatch.setattr(
        dashboard_module,
        "_prepare_chip_data_for_dashboard",
        lambda symbol, storage: (None, pd.DataFrame(), None),
    )

    payload = _build_dashboard_payload("2330")

    assert payload["ready"] is True
    assert isinstance(payload["multi_timeframe"], MultiTimeframeAnalysis)


def test_build_recent_institutional_table_keeps_last_five_days() -> None:
    inst = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=7, freq="D"),
            "foreign_net": [1000, 2000, 3000, 4000, 5000, 6000, 7000],
            "trust_net": [0, 1000, 0, 1000, 0, 1000, 0],
            "dealer_net": [-1000, -1000, -1000, -1000, -1000, -1000, -1000],
        }
    )

    table = _build_recent_institutional_table(inst, n_days=5)

    assert len(table) == 5
    assert list(table.columns) == ["日期", "外資", "投信", "自營商"]
    assert table.iloc[-1]["外資"] == 7


def test_style_recent_institutional_table_applies_red_green_and_keeps_negative_sign() -> None:
    table = pd.DataFrame(
        {
            "日期": ["2026-01-01", "2026-01-02", "2026-01-03"],
            "外資": [3, -2, 0],
            "投信": [0, 1, -1],
            "自營商": [-4, 0, 2],
        }
    )

    styled = _style_recent_institutional_table(table)

    assert styled._display_funcs[(0, 1)](table.iloc[0, 1]) == "3"
    assert styled._display_funcs[(1, 1)](table.iloc[1, 1]) == "-2"

    style_ctx = styled._compute().ctx
    assert ("color", "#dc2626") in style_ctx[(0, 1)]
    assert ("color", "#16a34a") in style_ctx[(1, 1)]
    assert (2, 1) not in style_ctx


def test_prepare_chip_data_returns_friendly_finmind_only_error(monkeypatch, tmp_path) -> None:
    import src.ui.pages.dashboard as dashboard_module

    class _BrokenFetcher:
        def fetch_institutional_incremental(self, symbol: str, storage):  # noqa: ANN001, ANN201
            raise RuntimeError("api timeout")

        def fetch_margin_incremental(self, symbol: str, storage):  # noqa: ANN001, ANN201
            return pd.DataFrame()

    monkeypatch.setattr(dashboard_module, "_build_chip_fetcher", lambda: _BrokenFetcher())

    chip, recent_df, chip_error = _prepare_chip_data_for_dashboard("2330", ParquetStorage(data_dir=tmp_path))

    assert chip is None
    assert recent_df.empty
    assert chip_error is not None
    assert "籌碼資料僅支援 FinMind，抓取失敗：" in chip_error


def test_sync_symbol_daily_data_fallback_when_primary_update_fails(monkeypatch) -> None:
    import src.ui.pages.dashboard as dashboard_module

    calls: list[str] = []

    class _Fetcher:
        def __init__(self, source: str):
            self.source = source

    class _Maintenance:
        def __init__(self, *, fetcher, **kwargs):  # noqa: ANN003
            self.fetcher = fetcher

        def update_daily(self, symbol: str) -> None:
            calls.append(f"{self.fetcher.source}:{symbol}")
            if self.fetcher.source == "finmind":
                raise RuntimeError("primary update failed")

    class _Meta:
        def close(self) -> None:
            return None

    monkeypatch.setattr(dashboard_module, "DuckDBMeta", _Meta)
    monkeypatch.setattr(dashboard_module, "DataMaintenance", _Maintenance)
    monkeypatch.setattr(
        dashboard_module,
        "_build_fetchers_from_config",
        lambda: [("finmind", _Fetcher("finmind")), ("yfinance", _Fetcher("yfinance"))],
    )

    dashboard_module._sync_symbol_daily_data("2330", storage=object())  # type: ignore[arg-type]

    assert calls == ["finmind:2330", "yfinance:2330"]
