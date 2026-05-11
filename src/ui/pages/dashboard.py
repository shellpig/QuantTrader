"""Stock dashboard page (Phase 8-F)."""

from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:  # pragma: no cover
    go = None

from src.ai.advisor import AIAdvisor, DashboardAnalysis
from src.analysis.chip_analysis import ChipSummary, generate_chip_summary
from src.analysis.pattern import (
    CandlePattern,
    ChartPatternResult,
    MultiTimeframeAnalysis,
    analyze_multi_timeframe,
    detect_candle_patterns,
    detect_chart_pattern,
)
from src.analysis.technical_summary import TechnicalSummary, generate_technical_summary
from src.core.config import get_config
from src.core.exceptions import AICallError, AIDisabledError
from src.data.cleaner import DataCleaner
from src.data.fetcher import FinMindFetcher, IDataFetcher, YFinanceFetcher
from src.data.maintenance import DataMaintenance
from src.data.realtime import BidAskStructure, RealtimeFetcher, RealtimeQuote
from src.data.storage import DuckDBMeta, ParquetStorage
from src.ui.themes import get_theme

_TW_SYMBOL_PATTERN = re.compile(r"^[0-9A-Z]{4,6}$")
_STATE_KEY = "dashboard_payload"
_KLINE_COUNT_OPTIONS = (30, 60, 90, 120, 180, 240, 360)


def render() -> None:
    render_dashboard_page()


def render_dashboard_page() -> None:
    """Render stock dashboard page."""
    st.title("個股分析")
    st.caption("整合技術面、籌碼、型態與 AI 劇本的個股儀表板。")

    symbol = st.text_input("股票代碼", value="", key="dashboard_symbol").strip().upper()
    analyze_clicked = st.button("分析", type="primary", key="dashboard_analyze")

    if not symbol:
        st.info("請先輸入股票代碼。")
        return
    if not _TW_SYMBOL_PATTERN.fullmatch(symbol):
        st.warning("股票代碼格式錯誤，請輸入 4~6 位英數台股代碼。")
        return

    if analyze_clicked:
        payload = _build_dashboard_payload(symbol)
        st.session_state[_STATE_KEY] = payload

    payload = st.session_state.get(_STATE_KEY)
    if not payload or payload.get("symbol") != symbol:
        st.info("輸入股票代碼後，點選「分析」。")
        return

    is_ready = bool(payload.get("ready", "technical" in payload))
    if not is_ready:
        st.warning(str(payload.get("error", "個股分析資料尚未準備完成。")))
        return

    tabs = st.tabs(["總覽", "籌碼與量價", "型態與週期", "AI 劇本"])
    with tabs[0]:
        refresh_clicked = _render_tab_overview(
            quote=payload.get("quote"),
            technical=payload["technical"],
            df=payload["daily_df"],
        )
    with tabs[1]:
        _render_tab_chip(
            chip=payload.get("chip"),
            bid_ask=payload.get("bid_ask"),
            technical=payload["technical"],
            chip_recent_df=payload.get("chip_recent_df"),
            chip_error=payload.get("chip_error"),
        )
    with tabs[2]:
        _render_tab_pattern(
            candle_patterns=payload["candle_patterns"],
            chart_patterns=payload["chart_patterns"],
            mtf=payload["multi_timeframe"],
        )
    with tabs[3]:
        _render_tab_ai(
            analysis=payload.get("analysis"),
            technical=payload["technical"],
            ai_enabled=payload["ai_enabled"],
        )

    if refresh_clicked:
        refreshed_quote, refreshed_bid_ask, refresh_error = _refresh_realtime_snapshot(symbol)
        if refreshed_quote is not None:
            payload["quote"] = refreshed_quote
        if refreshed_bid_ask is not None:
            payload["bid_ask"] = refreshed_bid_ask
        st.session_state[_STATE_KEY] = payload
        if refresh_error:
            st.warning(refresh_error)
        st.rerun()


def _build_dashboard_payload(symbol: str) -> dict[str, Any]:
    storage = ParquetStorage()
    daily, daily_error = _prepare_daily_data_for_dashboard(symbol, storage)
    if daily_error:
        return {
            "symbol": symbol,
            "ready": False,
            "error": daily_error,
        }

    if daily.empty:
        return {
            "symbol": symbol,
            "ready": False,
            "error": f"{symbol} 尚無可用日線資料。",
        }

    daily = _normalize_daily_df(daily)
    technical = generate_technical_summary(daily)

    quote: RealtimeQuote | None = None
    bid_ask: BidAskStructure | None = None
    try:
        realtime = RealtimeFetcher.from_config()
        quote = realtime.fetch_quote(symbol)
        bid_ask = realtime.fetch_bid_ask_structure(quote)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"即時行情暫時不可用，已改用日線資料顯示：{exc}")

    chip, chip_recent_df, chip_error = _prepare_chip_data_for_dashboard(symbol, storage)

    candle_patterns = detect_candle_patterns(daily)
    chart_patterns = detect_chart_pattern(daily)
    multi_timeframe = analyze_multi_timeframe(daily.set_index("date"))

    config = get_config()
    ai_section = config.get("ai", {}) if isinstance(config, dict) else {}
    ai_enabled = bool(ai_section.get("enabled", False))
    analysis: DashboardAnalysis | None = None
    if ai_enabled:
        try:
            advisor = AIAdvisor()
            analysis = advisor.generate_stock_dashboard_analysis(
                symbol=symbol,
                technical_summary=technical,
                chip_summary=chip,
                company_info=None,
                recent_prices=daily.tail(60),
            )
        except AIDisabledError:
            analysis = None
        except AICallError as exc:
            st.warning(f"AI 劇本生成失敗：{exc}")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"AI 劇本生成失敗：{exc}")

    return {
        "symbol": symbol,
        "ready": True,
        "error": None,
        "daily_df": daily,
        "technical": technical,
        "quote": quote,
        "bid_ask": bid_ask,
        "chip": chip,
        "chip_recent_df": chip_recent_df,
        "chip_error": chip_error,
        "candle_patterns": candle_patterns,
        "chart_patterns": chart_patterns,
        "multi_timeframe": multi_timeframe,
        "analysis": analysis,
        "ai_enabled": ai_enabled,
    }


def _prepare_daily_data_for_dashboard(symbol: str, storage: ParquetStorage) -> tuple[pd.DataFrame, str | None]:
    try:
        _sync_symbol_daily_data(symbol, storage)
    except Exception as exc:  # noqa: BLE001
        return pd.DataFrame(), f"{symbol} 日線資料更新失敗：{exc}"
    return storage.load_daily(symbol), None


def _prepare_chip_data_for_dashboard(
    symbol: str,
    storage: ParquetStorage,
) -> tuple[ChipSummary | None, pd.DataFrame, str | None]:
    try:
        fetcher = _build_chip_fetcher()
        institutional_df = fetcher.fetch_institutional_incremental(symbol, storage)
        margin_df = fetcher.fetch_margin_incremental(symbol, storage)
    except Exception as exc:  # noqa: BLE001
        return None, pd.DataFrame(), f"籌碼資料僅支援 FinMind，抓取失敗：{exc}"

    if institutional_df.empty and margin_df.empty:
        return None, pd.DataFrame(), "目前無可用籌碼資料。"

    chip = generate_chip_summary(institutional_df, margin_df, n_days=5)
    recent_df = _build_recent_institutional_table(institutional_df, n_days=5)
    return chip, recent_df, None


def _build_recent_institutional_table(institutional_df: pd.DataFrame, *, n_days: int = 5) -> pd.DataFrame:
    required = {"date", "foreign_net", "trust_net", "dealer_net"}
    if institutional_df.empty or not required.issubset(institutional_df.columns):
        return pd.DataFrame(columns=["日期", "外資", "投信", "自營商"])

    out = institutional_df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").tail(max(1, int(n_days))).copy()
    if out.empty:
        return pd.DataFrame(columns=["日期", "外資", "投信", "自營商"])

    for col in ("foreign_net", "trust_net", "dealer_net"):
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    return pd.DataFrame(
        {
            "日期": out["date"].dt.strftime("%Y-%m-%d"),
            "外資": (out["foreign_net"] / 1000.0).astype(int),
            "投信": (out["trust_net"] / 1000.0).astype(int),
            "自營商": (out["dealer_net"] / 1000.0).astype(int),
        }
    ).reset_index(drop=True)


def _style_recent_institutional_table(table: pd.DataFrame) -> pd.io.formats.style.Styler:
    value_cols = [col for col in table.columns if col != "日期"]

    def _color_for_net_value(value: object) -> str:
        number = pd.to_numeric(value, errors="coerce")
        if pd.isna(number):
            return ""
        if number > 0:
            return "color: #dc2626"
        if number < 0:
            return "color: #16a34a"
        return ""

    format_map = {col: "{:d}" for col in value_cols}
    return table.style.format(format_map).map(_color_for_net_value, subset=value_cols)


def _sync_symbol_daily_data(symbol: str, storage: ParquetStorage) -> None:
    fetchers = _build_fetchers_from_config()
    if not fetchers:
        raise RuntimeError("No available data source. Details: n/a")

    errors: list[str] = []
    for source, fetcher in fetchers:
        meta = DuckDBMeta()
        try:
            maintenance = DataMaintenance(
                fetcher=fetcher,
                storage=storage,
                meta=meta,
                cleaner=DataCleaner(),
            )
            maintenance.update_daily(symbol)
            return
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")
        finally:
            meta.close()

    raise RuntimeError(f"Daily data update failed for all sources. Details: {' | '.join(errors)}")


def _build_chip_fetcher() -> FinMindFetcher:
    config = get_config()
    data_section = config.get("data", {}) if isinstance(config, dict) else {}
    primary = str(data_section.get("primary_source", "finmind")).strip().lower()
    fallback = str(data_section.get("fallback_source", "yfinance")).strip().lower()
    order = [primary, fallback]

    errors: list[str] = []
    for source in order:
        if source != "finmind":
            continue
        try:
            return FinMindFetcher()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")

    raise RuntimeError(
        f"No available chip fetcher. Details: {' | '.join(errors) if errors else 'finmind not configured'}"
    )


def _build_fetcher_from_config() -> IDataFetcher:
    fetchers = _build_fetchers_from_config()
    if fetchers:
        return fetchers[0][1]
    raise RuntimeError("No available data source. Details: n/a")


def _build_fetchers_from_config() -> list[tuple[str, IDataFetcher]]:
    config = get_config()
    data_section = config.get("data", {}) if isinstance(config, dict) else {}
    primary = str(data_section.get("primary_source", "finmind")).strip().lower()
    fallback = str(data_section.get("fallback_source", "yfinance")).strip().lower()
    order = [primary, fallback]

    fetchers: list[tuple[str, IDataFetcher]] = []
    for source in order:
        if source in {name for name, _ in fetchers}:
            continue
        try:
            if source == "finmind":
                fetchers.append((source, FinMindFetcher()))
            elif source == "yfinance":
                fetchers.append((source, YFinanceFetcher()))
        except Exception:  # noqa: BLE001
            continue
    return fetchers


def _normalize_daily_df(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    for col in ("open", "high", "low", "close", "volume"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close", "volume"])
    return out.reset_index(drop=True)


def _render_tab_overview(
    quote: RealtimeQuote | None,
    technical: TechnicalSummary,
    df: pd.DataFrame,
) -> bool:
    st.subheader("行情總覽")
    latest_close = _safe_latest_daily_value(df, "close")
    latest_volume = _safe_latest_daily_int(df, "volume")
    if quote is not None and quote.is_market_open:
        bid1 = quote.best_bid[0] if quote.best_bid else None
        ask1 = quote.best_ask[0] if quote.best_ask else None
        price_for_change = float(bid1) if bid1 is not None else float(quote.price)
        change = float(price_for_change - quote.yesterday_close)
        change_pct = float((change / quote.yesterday_close * 100.0) if quote.yesterday_close else 0.0)
        cols = st.columns(6)
        cols[0].metric("買一", _format_price_or_na(bid1))
        cols[1].metric("賣一", _format_price_or_na(ask1))
        cols[2].metric("漲跌", f"{change:+.2f}")
        cols[3].metric("漲跌幅", f"{change_pct:+.2f}%")
        cols[4].metric("盤中量(張)", f"{max(0, int(quote.volume)):,}")
        cols[5].metric("狀態", "盤中資料")
    elif quote is not None:
        close_for_display = latest_close if latest_close is not None else quote.price
        daily_volume_for_display = latest_volume if latest_volume is not None else int(quote.volume)
        change = float(close_for_display - quote.yesterday_close)
        change_pct = float((change / quote.yesterday_close * 100.0) if quote.yesterday_close else 0.0)
        cols = st.columns(5)
        cols[0].metric("收盤價", f"{close_for_display:.2f}")
        cols[1].metric("漲跌", f"{change:+.2f}")
        cols[2].metric("漲跌幅", f"{change_pct:+.2f}%")
        cols[3].metric("日成交量(張)", f"{max(0, int(daily_volume_for_display)):,}")
        cols[4].metric("狀態", "盤後資料")
    else:
        st.info("目前未取得即時報價，以下以日線資料顯示。")

    _, op_col = st.columns([4, 1])
    with op_col:
        k_count = st.selectbox(
            "K棒數量",
            options=_KLINE_COUNT_OPTIONS,
            index=_KLINE_COUNT_OPTIONS.index(120),
            key="dashboard_kline_count",
        )
    _render_price_chart(df, technical, int(k_count))

    st.markdown("**技術分析總覽**")
    row1 = st.columns(3)
    row1[0].metric("趨勢方向", technical.trend_direction)
    row1[1].metric("均線狀態", technical.ma_status)
    row1[2].metric("KD 狀態", technical.kd_status)
    row2 = st.columns(3)
    row2[0].metric("MACD 狀態", technical.macd_status)
    row2[1].metric("量能狀態", technical.volume_status)
    row2[2].metric("量價關係", technical.volume_price_relation)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**壓力區**")
        if technical.resistance_levels:
            for lvl in technical.resistance_levels:
                st.write(f"- {lvl.label}: {lvl.value:.2f}")
        else:
            st.write("- 尚無資料")
    with c2:
        st.markdown("**支撐區**")
        if technical.support_levels:
            for lvl in technical.support_levels:
                st.write(f"- {lvl.label}: {lvl.value:.2f}")
        else:
            st.write("- 尚無資料")

    st.markdown("**短線綜合分數**")
    score_pct = max(0.0, min(1.0, float(technical.short_term_score)))
    st.progress(score_pct, text=f"{technical.short_term_label}（{score_pct * 100:.1f}%）")
    refresh_clicked = st.button("重新整理報價", key="dashboard_refresh_quote", help="重新查詢即時報價")
    return bool(refresh_clicked)


def _format_price_or_na(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f}"


def _safe_latest_daily_value(df: pd.DataFrame, column: str) -> float | None:
    if df.empty or column not in df.columns:
        return None
    series = pd.to_numeric(df[column], errors="coerce").dropna()
    if series.empty:
        return None
    return float(series.iloc[-1])


def _safe_latest_daily_int(df: pd.DataFrame, column: str) -> int | None:
    value = _safe_latest_daily_value(df, column)
    if value is None:
        return None
    return int(value)


def _refresh_realtime_snapshot(symbol: str) -> tuple[RealtimeQuote | None, BidAskStructure | None, str | None]:
    try:
        realtime = RealtimeFetcher.from_config()
        quote = realtime.fetch_quote(symbol)
        bid_ask = realtime.fetch_bid_ask_structure(quote)
        return quote, bid_ask, None
    except Exception as exc:  # noqa: BLE001
        return None, None, f"即時報價更新失敗：{exc}"


def _render_price_chart(df: pd.DataFrame, technical: TechnicalSummary, kline_count: int) -> None:
    if go is None or df.empty:
        return
    config = get_config()
    ui = config.get("ui", {}) if isinstance(config, dict) else {}
    theme_name = str(ui.get("theme", "midnight_blue"))
    _, palette = get_theme(theme_name)

    chart_df = df.copy()
    chart_df["ma5"] = chart_df["close"].rolling(5).mean()
    chart_df["ma20"] = chart_df["close"].rolling(20).mean()
    chart_df["ma60"] = chart_df["close"].rolling(60).mean()
    chart_df = chart_df.tail(max(1, int(kline_count))).reset_index(drop=True)

    price_min = float(chart_df["low"].min())
    price_max = float(chart_df["high"].max())
    y_padding = (price_max - price_min) * 0.05

    dates = chart_df["date"]

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=dates,
            open=chart_df["open"],
            high=chart_df["high"],
            low=chart_df["low"],
            close=chart_df["close"],
            name="日K",
            increasing_line_color="#ef4444",
            increasing_fillcolor="#ef4444",
            decreasing_line_color="#22c55e",
            decreasing_fillcolor="#22c55e",
        )
    )
    fig.add_trace(go.Scatter(x=dates, y=chart_df["ma5"], mode="lines", name="MA5", line={"width": 1}))
    fig.add_trace(go.Scatter(x=dates, y=chart_df["ma20"], mode="lines", name="MA20", line={"width": 1}))
    fig.add_trace(go.Scatter(x=dates, y=chart_df["ma60"], mode="lines", name="MA60", line={"width": 1}))

    seg_x0 = dates.iloc[max(0, len(dates) - 20)]
    seg_x1 = dates.iloc[-1]
    for level in technical.resistance_levels:
        y = float(level.value)
        fig.add_shape(type="line", x0=seg_x0, x1=seg_x1, y0=y, y1=y, xref="x", yref="y",
                      line={"dash": "dot", "color": "#ef4444", "width": 1})
        fig.add_annotation(x=seg_x1, y=y, xref="x", yref="y", text=f" 壓 {y:.1f}",
                           showarrow=False, font={"size": 10, "color": "#ef4444"}, xanchor="left")
    for level in technical.support_levels:
        y = float(level.value)
        fig.add_shape(type="line", x0=seg_x0, x1=seg_x1, y0=y, y1=y, xref="x", yref="y",
                      line={"dash": "dot", "color": "#22c55e", "width": 1})
        fig.add_annotation(x=seg_x1, y=y, xref="x", yref="y", text=f" 撐 {y:.1f}",
                           showarrow=False, font={"size": 10, "color": "#22c55e"}, xanchor="left")

    fig.update_layout(
        template=palette["plotly_template"],
        title="日K + 均線 + 支撐壓力",
        xaxis_title="日期",
        xaxis_rangeslider={"visible": True, "thickness": 0.04},
        xaxis_rangebreaks=[{"bounds": ["sat", "mon"]}],
        yaxis_title="價格",
        yaxis_autorange=True,
        yaxis_fixedrange=True,
        font={"color": palette["text"]},
        height=650,
        dragmode="pan",
    )
    st.plotly_chart(fig, width="stretch")


def _render_tab_chip(
    chip: ChipSummary | None,
    bid_ask: BidAskStructure | None,
    technical: TechnicalSummary,
    chip_recent_df: pd.DataFrame | None = None,
    chip_error: str | None = None,
) -> None:
    st.subheader("籌碼與量價")
    if chip_error:
        st.info(chip_error)

    if chip is None:
        if not chip_error:
            st.info("尚未載入籌碼資料")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("外資近N日", chip.foreign_label)
        c2.metric("投信近N日", chip.trust_label)
        c3.metric("自營商近N日", chip.dealer_label)
        st.write(f"籌碼集中度：{chip.chip_concentration} / 趨勢：{chip.chip_trend}")
        st.caption(chip.chip_description)
        c4, c5 = st.columns(2)
        c4.metric("融資餘額變化(張)", f"{chip.margin_balance_change:+d}")
        c5.metric("融券餘額變化(張)", f"{chip.short_balance_change:+d}")
        st.markdown("**近 5 交易日三大法人（張）**")
        if chip_recent_df is not None and not chip_recent_df.empty:
            st.dataframe(_style_recent_institutional_table(chip_recent_df), width="stretch", hide_index=True)
        else:
            st.info("目前無可顯示的近 5 交易日三大法人資料。")

    if bid_ask is not None:
        st.metric("買賣力道估算", bid_ask.label)
        st.caption(f"買方佔比 {bid_ask.bid_ratio:.2%} / 賣方佔比 {bid_ask.ask_ratio:.2%}")
    else:
        st.info("尚未取得五檔買賣量，買賣力道暫不可用。")

    st.markdown("**量價結構分析**")
    st.write(technical.volume_price_divergence or "資料不足")
    st.write(technical.ma_bias or "資料不足")
    st.write(technical.operation_observation or "資料不足")


def _render_tab_pattern(
    candle_patterns: list[CandlePattern],
    chart_patterns: list[ChartPatternResult],
    mtf: MultiTimeframeAnalysis,
) -> None:
    st.subheader("型態與週期")
    detected = [p for p in candle_patterns if p.detected]
    not_detected = [p for p in candle_patterns if not p.detected]
    if detected:
        st.markdown("**偵測到的型態：**")
        for p in detected:
            st.success(f"**{p.name}** — {p.description}")
    if not_detected:
        with st.expander("未偵測到的型態", expanded=False):
            rows = [{"型態": p.name, "說明": p.description} for p in not_detected]
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

    for pattern in chart_patterns:
        if pattern.formed:
            st.success(f"{pattern.pattern_type}：{pattern.description}")
            if pattern.key_points:
                st.caption(", ".join(f"{name}={value:.2f}" for name, value in pattern.key_points if name != "索引區間"))
        else:
            st.info(f"{pattern.pattern_type}：{pattern.description}")

    c1, c2, c3 = st.columns(3)
    c1.metric("日線", f"{mtf.daily.trend_direction} / {mtf.daily.strength}")
    c2.metric("週線", f"{mtf.weekly.trend_direction} / {mtf.weekly.strength}")
    c3.metric("月線", f"{mtf.monthly.trend_direction} / {mtf.monthly.strength}")


def _render_tab_ai(
    analysis: DashboardAnalysis | None,
    technical: TechnicalSummary,
    ai_enabled: bool,
) -> None:
    st.subheader("AI 劇本")
    if not ai_enabled or analysis is None:
        st.info("請啟用 AI 功能")
        st.write(technical.operation_observation or "目前無可用的 rule-based 結論。")
        return

    st.markdown("**產業概況**")
    for item in analysis.industry_overview:
        st.write(f"- {item}")
    st.markdown("**公司概況**")
    for item in analysis.company_overview:
        st.write(f"- {item}")

    st.markdown("**量價分析**")
    st.write(analysis.volume_price_analysis)

    st.markdown("**三情境操作劇本**")
    scenario_rows = [asdict(item) for item in analysis.scenarios]
    st.dataframe(pd.DataFrame(scenario_rows), width="stretch", hide_index=True)

    st.markdown("**整體結論**")
    st.success(analysis.conclusion)
    st.caption("非投資建議，僅供研究與風險控管參考。")


if __name__ == "__main__":
    render_dashboard_page()
