"""Backtest page."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import streamlit as st

try:
    import plotly.graph_objects as go
except ModuleNotFoundError:  # pragma: no cover - optional in some runtime environments
    go = None

try:
    from streamlit_extras.metric_cards import style_metric_cards
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False

from src.backtest.engine_event import EventDrivenBacktester
from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.report import TearsheetReport
from src.backtest.dca import DcaBacktestResult, run_dca_backtest
from src.core.config import get_config
from src.core.constants import TAIPEI_TZ
from src.core.exceptions import FetcherError
from src.core.strategy_config import get_strategy_presets, make_strategy_label
from src.data.fetcher import FinMindFetcher
from src.data.storage import ParquetStorage
from src.strategy.examples.ma_cross import MACrossStrategy

_TW_SYMBOL_PATTERN = re.compile(r"^\d{4,6}$")
_VECTOR_ENGINE_LABEL = "向量化引擎"
_EVENT_ENGINE_LABEL = "事件驅動引擎"
_TRADE_MARKER_BASE_SIZE = 10
_TRADE_MARKER_HEIGHT_MULTIPLIER = 2.5
_TRADE_MARKER_STEM_SIZE = int(round(_TRADE_MARKER_BASE_SIZE * _TRADE_MARKER_HEIGHT_MULTIPLIER))


def render() -> None:
    st.title("回測")
    st.caption("執行策略回測、查看 Tearsheet，並補充股價均線與 EPS 資訊。")

    today = pd.Timestamp.today().date()
    default_start = (pd.Timestamp.today() - pd.Timedelta(days=365 * 3)).date()

    c1, c2 = st.columns(2)
    with c1:
        symbol = st.text_input("股票代碼", value="2330").strip()
        start_date = st.date_input("開始日期", value=default_start)
    with c2:
        engine_name = st.selectbox("回測引擎", options=[_VECTOR_ENGINE_LABEL, _EVENT_ENGINE_LABEL], index=0)
        end_date = st.date_input("結束日期", value=today)

    strategy_presets = get_strategy_presets(get_config())
    strategy_labels = [make_strategy_label(preset) for preset in strategy_presets]
    strategy_label = st.selectbox("策略", options=strategy_labels, index=0)
    selected_strategy = strategy_presets[strategy_labels.index(strategy_label)]
    selected_type = str(selected_strategy.get("type", "")).strip().lower()
    selected_params = selected_strategy.get("params", {}) if isinstance(selected_strategy.get("params"), dict) else {}

    if selected_type == "moving_average_cross":
        st.caption(
            f"策略參數：short_window={int(selected_params.get('short_window', 20))}, "
            f"long_window={int(selected_params.get('long_window', 60))}"
        )
    elif selected_type == "dollar_cost_averaging":
        st.caption(
            "策略參數："
            f"monthly_day={int(selected_params.get('monthly_day', 5))}, "
            f"monthly_amount={float(selected_params.get('monthly_amount', 10_000)):.0f}, "
            f"min_buy_unit={int(selected_params.get('min_buy_unit', 1))}, "
            f"non_trading_day_policy={str(selected_params.get('non_trading_day_policy', 'next_trading_day'))}, "
            f"buy_price_field={str(selected_params.get('buy_price_field', 'close'))}"
        )
    else:
        st.warning(f"此策略類型目前未支援執行：{selected_type}")

    if st.button("開始回測", type="primary"):
        _run_backtest(
            symbol=symbol,
            start_date=pd.Timestamp(start_date),
            end_date=pd.Timestamp(end_date),
            engine_name=engine_name,
            strategy_preset=selected_strategy,
        )


def _run_backtest(
    *,
    symbol: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    engine_name: str,
    strategy_preset: dict[str, object],
) -> None:
    if not _TW_SYMBOL_PATTERN.fullmatch(symbol):
        st.error("股票代碼格式錯誤，請輸入 4 到 6 碼台股代碼。")
        return

    start_ts = _as_taipei_start(start_date)
    end_exclusive = _as_taipei_start(end_date) + pd.Timedelta(days=1)
    if end_exclusive <= start_ts:
        st.error("結束日期必須晚於開始日期。")
        return

    try:
        data = _load_backtest_data(
            symbol=symbol,
            start_ts=start_ts,
            end_exclusive=end_exclusive,
            require_adjusted=True,
        )
    except Exception as exc:  # noqa: BLE001
        st.error(f"讀取資料失敗：{exc}")
        return

    strategy_type = str(strategy_preset.get("type", "")).strip().lower()
    strategy_params = strategy_preset.get("params", {}) if isinstance(strategy_preset.get("params"), dict) else {}

    if data.empty and strategy_type != "dollar_cost_averaging":
        st.warning("資料區間內沒有可用日線資料。")
        return

    try:
        if strategy_type == "moving_average_cross":
            ma_short = int(strategy_params.get("short_window", 20))
            ma_long = int(strategy_params.get("long_window", 60))
            if ma_short >= ma_long:
                st.error("策略參數錯誤：short_window 必須小於 long_window。")
                return

            strategy = MACrossStrategy(ma_short=ma_short, ma_long=ma_long)
            engine = VectorizedBacktester() if engine_name == _VECTOR_ENGINE_LABEL else EventDrivenBacktester()
            result = engine.run(strategy=strategy, data=data)

            report = TearsheetReport(result)
            figures = report.get_streamlit_figures()

            m0, m1, m2, m3, m4 = st.columns(5)
            m0.metric("交易次數", f"{int(result.total_trades)}")
            m1.metric("總報酬率", f"{result.total_return * 100:.2f}%")
            m2.metric("年化報酬率", f"{result.annual_return * 100:.2f}%")
            m3.metric("最大回撤", f"{result.max_drawdown * 100:.2f}%")
            m4.metric("Sharpe", f"{result.sharpe_ratio:.2f}")

            config = get_config()
            ui_section = config.get("ui", {}) if isinstance(config, dict) else {}
            use_extras = bool(ui_section.get("use_extras", True))
            if use_extras and HAS_EXTRAS:
                style_metric_cards()

            st.plotly_chart(figures["equity"], use_container_width=True)
            st.plotly_chart(figures["drawdown"], use_container_width=True)
            st.plotly_chart(figures["monthly"], use_container_width=True)
            st.plotly_chart(figures["summary"], use_container_width=True)

            st.divider()
            _render_price_panel(price_df=data, trades=result.trades, symbol=symbol)
            st.divider()
            _render_eps_panel(symbol=symbol, end_ts=end_exclusive - pd.Timedelta(days=1))
            return

        if strategy_type == "dollar_cost_averaging":
            if engine_name != _VECTOR_ENGINE_LABEL:
                st.info("定期定額策略使用專用回測流程，已忽略回測引擎選擇。")

            dca_result = run_dca_backtest(
                data=data,
                symbol=symbol,
                start_ts=start_ts,
                end_exclusive=end_exclusive,
                params=strategy_params,
            )
            _render_dca_summary(dca_result)
            _render_dca_transactions(dca_result.transactions)

            trade_markers = _dca_transactions_to_trade_markers(dca_result.transactions)
            st.divider()
            _render_price_panel(price_df=data, trades=trade_markers, symbol=symbol)
            st.divider()
            _render_eps_panel(symbol=symbol, end_ts=end_exclusive - pd.Timedelta(days=1))
            return

        st.error(f"目前不支援策略類型：{strategy_type}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"回測執行失敗：{exc}")


def _render_dca_summary(result: DcaBacktestResult) -> None:
    st.subheader("定期定額回測摘要")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("累積投入金額", f"{result.cumulative_invested:,.2f}")
    c2.metric("目前市值", f"{result.market_value:,.2f}")
    c3.metric("帳戶現金", f"{result.cash_balance:,.2f}")
    c4.metric("未實現損益", f"{result.unrealized_pnl:,.2f}")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("總報酬率", f"{result.total_return_rate * 100:.2f}%")
    c6.metric("累積買入股數", f"{result.cumulative_shares:,}")
    c7.metric("平均成本", f"{result.average_cost:,.4f}")
    c8.metric("投入次數", f"{result.contribution_count}")

    config = get_config()
    ui_section = config.get("ui", {}) if isinstance(config, dict) else {}
    use_extras = bool(ui_section.get("use_extras", True))
    if use_extras and HAS_EXTRAS:
        style_metric_cards()


def _render_dca_transactions(transactions: pd.DataFrame) -> None:
    st.subheader("定期定額交易紀錄")
    if transactions is None or transactions.empty:
        st.info("尚無定期定額交易紀錄。")
        return

    reason_labels = {
        "": "",
        "NO_TRADING_DATES": "無交易日資料",
        "NO_TRADING_DAY_UNTIL_MONTH_END": "指定日後至月底無交易日",
        "NO_TRADING_DAY_AFTER_MONTH_END": "月底後無可順延交易日",
        "BUY_DATE_PRICE_MISSING": "買入日價格缺失",
        "INVALID_BUY_PRICE": "買入價無效",
        "INSUFFICIENT_FOR_MIN_BUY_UNIT": "投入金額不足買入最小單位",
    }

    view = transactions.copy()
    view["date"] = pd.to_datetime(view["date"], errors="coerce")
    view["reason"] = view["reason"].map(lambda v: reason_labels.get(str(v), str(v)))
    view["status"] = view["status"].map(lambda v: "成功" if str(v).upper() == "FILLED" else "略過")

    display = pd.DataFrame(
        {
            "日期": view["date"].dt.strftime("%Y-%m-%d"),
            "狀態": view["status"],
            "原因": view["reason"],
            "投入金額": view["invested_amount"],
            "買入價格": view["buy_price"],
            "買入股數": view["buy_shares"],
            "手續費": view["commission"],
            "實際花費": view["spend"],
            "剩餘現金": view["cash_balance"],
            "累積股數": view["cumulative_shares"],
            "累積投入": view["cumulative_invested"],
            "平均成本": view["average_cost"],
        }
    )
    st.dataframe(display, use_container_width=True, hide_index=True)


def _dca_transactions_to_trade_markers(transactions: pd.DataFrame) -> pd.DataFrame:
    if transactions is None or transactions.empty:
        return pd.DataFrame(columns=["entry_date", "entry_price", "quantity", "exit_date", "exit_price"])

    filled = transactions.copy()
    filled["status"] = filled["status"].astype(str).str.upper()
    filled = filled[(filled["status"] == "FILLED") & (pd.to_numeric(filled["buy_shares"], errors="coerce") > 0)].copy()
    if filled.empty:
        return pd.DataFrame(columns=["entry_date", "entry_price", "quantity", "exit_date", "exit_price"])

    return pd.DataFrame(
        {
            "entry_date": pd.to_datetime(filled["date"], errors="coerce"),
            "entry_price": pd.to_numeric(filled["buy_price"], errors="coerce"),
            "quantity": pd.to_numeric(filled["buy_shares"], errors="coerce"),
            "exit_date": pd.NaT,
            "exit_price": float("nan"),
        }
    )


def _load_backtest_data(
    *,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    require_adjusted: bool = True,
) -> pd.DataFrame:
    storage = ParquetStorage()
    df = storage.load_adjusted(symbol)
    if df.empty and require_adjusted:
        raise FetcherError(
            f"{symbol} adjusted data is missing. Please run rebuild_adj_factors (or rebuild_symbol) before backtest."
        )
    if df.empty:
        df = storage.load_daily(symbol)
    if df.empty:
        return df

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).copy()
    if data["date"].dt.tz is None:
        data["date"] = data["date"].dt.tz_localize(TAIPEI_TZ)
    else:
        data["date"] = data["date"].dt.tz_convert(TAIPEI_TZ)

    for col in ("open", "high", "low", "close"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close"])
    data = data[(data["date"] >= start_ts) & (data["date"] < end_exclusive)].copy()
    return data.sort_values("date").reset_index(drop=True)


def _render_price_panel(*, price_df: pd.DataFrame, trades: pd.DataFrame, symbol: str) -> None:
    st.subheader("股價走勢、均線與成交點位")
    if price_df.empty:
        st.info("本區間沒有可顯示的股價資料。")
        return

    features = _build_price_features(price_df)
    if go is None:
        st.warning("缺少 plotly，改以表格顯示。")
        st.dataframe(features[["date", "close", "ma5", "ma20", "ma60"]], use_container_width=True)
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=features["date"],
            y=features["close"],
            mode="lines",
            name="收盤價",
            line={"color": "#1f77b4", "width": 2},
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=features["date"],
            y=features["ma5"],
            mode="lines",
            name="週線 MA5",
            line={"color": "#ff7f0e", "width": 1.6},
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=features["date"],
            y=features["ma20"],
            mode="lines",
            name="月線 MA20",
            line={"color": "#2ca02c", "width": 1.6},
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=features["date"],
            y=features["ma60"],
            mode="lines",
            name="季線 MA60",
            line={"color": "#9467bd", "width": 1.6},
            hoverinfo="skip",
        )
    )

    buy_marks, sell_marks = _extract_trade_markers(trades=trades)
    _add_trade_marker_traces(
        fig=fig,
        marks=buy_marks,
        label="買進點",
        hover_title="買進",
        color="#d62728",
        tip_symbol="triangle-up",
        stem_symbol="line-ns-open",
    )
    _add_trade_marker_traces(
        fig=fig,
        marks=sell_marks,
        label="賣出點",
        hover_title="賣出",
        color="#17becf",
        tip_symbol="triangle-down",
        stem_symbol="line-ns-open",
    )

    hover_frame = _build_hover_alignment_frame(features)
    fig.add_trace(
        go.Scatter(
            x=hover_frame["calendar_date"],
            y=hover_frame["close"],
            mode="lines+markers",
            showlegend=False,
            name="",
            line={"width": 1, "color": "rgba(0,0,0,0.001)"},
            marker={"size": 8, "color": "rgba(0,0,0,0.001)"},
            customdata=hover_frame[
                ["trade_date_text", "close_text", "ma5_text", "ma20_text", "ma60_text"]
            ].to_numpy(),
            hovertemplate=(
                "日期: %{customdata[0]}<br>"
                "收盤價: %{customdata[1]}<br>"
                "週線 MA5: %{customdata[2]}<br>"
                "月線 MA20: %{customdata[3]}<br>"
                "季線 MA60: %{customdata[4]}<extra></extra>"
            ),
        )
    )

    from src.ui.themes import get_theme
    config = get_config()
    ui_section = config.get("ui", {}) if isinstance(config, dict) else {}
    theme_name = str(ui_section.get("theme", "arctic_light"))
    _, palette = get_theme(theme_name)

    fig.update_layout(
        template=palette["plotly_template"],
        paper_bgcolor=palette["surface"],
        plot_bgcolor=palette["surface"],
        title=f"{symbol} 回測區間走勢",
        xaxis_title="日期",
        yaxis_title="價格",
        hovermode="closest",
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("均線使用日收盤價 rolling mean 計算：MA5、MA20、MA60。")


def _build_price_features(price_df: pd.DataFrame) -> pd.DataFrame:
    out = price_df[["date", "close"]].copy()
    out = out.sort_values("date").reset_index(drop=True)
    out["ma5"] = out["close"].rolling(window=5).mean()
    out["ma20"] = out["close"].rolling(window=20).mean()
    out["ma60"] = out["close"].rolling(window=60).mean()
    return out


def _extract_trade_markers(*, trades: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if trades is None or trades.empty:
        return (
            pd.DataFrame(columns=["date", "price", "quantity"]),
            pd.DataFrame(columns=["date", "price", "quantity"]),
        )

    buys = pd.DataFrame(
        {
            "date": pd.to_datetime(trades.get("entry_date"), errors="coerce"),
            "price": pd.to_numeric(trades.get("entry_price"), errors="coerce"),
            "quantity": pd.to_numeric(trades.get("quantity"), errors="coerce"),
        }
    ).dropna(subset=["date", "price"])

    sells = pd.DataFrame(
        {
            "date": pd.to_datetime(trades.get("exit_date"), errors="coerce"),
            "price": pd.to_numeric(trades.get("exit_price"), errors="coerce"),
            "quantity": pd.to_numeric(trades.get("quantity"), errors="coerce"),
        }
    ).dropna(subset=["date", "price"])
    return buys.sort_values("date"), sells.sort_values("date")


def _add_trade_marker_traces(
    *,
    fig: go.Figure,
    marks: pd.DataFrame,
    label: str,
    hover_title: str,
    color: str,
    tip_symbol: str,
    stem_symbol: str,
) -> None:
    if marks.empty:
        return

    enriched = marks.copy()
    enriched["quantity_text"] = enriched.get("quantity", pd.Series(dtype="float64")).map(_format_quantity_value)

    # Invisible hover target to prioritize trade info around marker positions.
    fig.add_trace(
        go.Scatter(
            x=enriched["date"],
            y=enriched["price"],
            mode="markers",
            showlegend=False,
            legendgroup=label,
            marker={"symbol": "circle", "size": max(_TRADE_MARKER_STEM_SIZE, 24), "color": "rgba(0,0,0,0)"},
            customdata=enriched[["quantity_text"]].to_numpy(),
            hovertemplate=(
                f"{hover_title}: %{{x|%Y-%m-%d}}<br>"
                "成交價: %{y:.2f}<br>"
                "數量: %{customdata[0]}<extra></extra>"
            ),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=enriched["date"],
            y=enriched["price"],
            mode="markers",
            showlegend=False,
            legendgroup=label,
            marker={"symbol": stem_symbol, "size": _TRADE_MARKER_STEM_SIZE, "color": color, "line": {"width": 1}},
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=enriched["date"],
            y=enriched["price"],
            mode="markers",
            name=label,
            legendgroup=label,
            marker={"symbol": tip_symbol, "size": _TRADE_MARKER_BASE_SIZE, "color": color},
            hoverinfo="skip",
        )
    )


def _build_hover_alignment_frame(price_df: pd.DataFrame) -> pd.DataFrame:
    if price_df.empty:
        return pd.DataFrame(
            columns=[
                "calendar_date",
                "trade_date_text",
                "close",
                "close_text",
                "ma5_text",
                "ma20_text",
                "ma60_text",
            ]
        )

    trading_dates = pd.DatetimeIndex(price_df["date"])
    calendar_dates = pd.date_range(
        start=trading_dates.min().normalize(),
        end=trading_dates.max().normalize(),
        freq="D",
        tz=trading_dates.tz,
    )
    nearest_idx = _nearest_trading_indices(calendar_dates, trading_dates)
    aligned = price_df.iloc[nearest_idx].reset_index(drop=True)

    frame = pd.DataFrame(
        {
            "calendar_date": calendar_dates,
            "trade_date_text": aligned["date"].dt.strftime("%Y-%m-%d"),
            "close": aligned["close"],
            "close_text": aligned["close"].map(_format_price_value),
            "ma5_text": aligned["ma5"].map(_format_price_value),
            "ma20_text": aligned["ma20"].map(_format_price_value),
            "ma60_text": aligned["ma60"].map(_format_price_value),
        }
    )
    return frame


def _nearest_trading_indices(target_dates: pd.DatetimeIndex, trading_dates: pd.DatetimeIndex) -> np.ndarray:
    if len(trading_dates) == 0:
        return np.array([], dtype="int64")

    targets = _to_utc_index(target_dates)
    trades = _to_utc_index(trading_dates)

    trade_ns = trades.asi8
    target_ns = targets.asi8
    insert_pos = np.searchsorted(trade_ns, target_ns, side="left")

    prev_idx = np.clip(insert_pos - 1, 0, len(trade_ns) - 1)
    next_idx = np.clip(insert_pos, 0, len(trade_ns) - 1)

    chosen = prev_idx.copy()
    no_prev = insert_pos == 0
    chosen[no_prev] = next_idx[no_prev]

    between = (insert_pos > 0) & (insert_pos < len(trade_ns))
    if np.any(between):
        prev_dist = np.abs(target_ns[between] - trade_ns[prev_idx[between]])
        next_dist = np.abs(trade_ns[next_idx[between]] - target_ns[between])
        use_next = next_dist <= prev_dist  # tie goes to future trading day
        chosen[between] = np.where(use_next, next_idx[between], prev_idx[between])

    return chosen.astype("int64")


def _to_utc_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if index.tz is None:
        return index.tz_localize(TAIPEI_TZ).tz_convert("UTC")
    return index.tz_convert("UTC")


def _format_price_value(value: float) -> str:
    if pd.isna(value):
        return "尚無資料"
    return f"{float(value):.2f}"


def _format_quantity_value(value: float) -> str:
    if pd.isna(value):
        return "尚無資料"
    return f"{int(round(float(value))):,} 股"


def _render_eps_panel(*, symbol: str, end_ts: pd.Timestamp) -> None:
    st.subheader("近 15 年 EPS 紀錄")

    end_year = pd.Timestamp(end_ts).year
    start_year = end_year - 14
    start_date = f"{start_year}-01-01"

    try:
        fetcher = FinMindFetcher()
        eps_df = fetcher.fetch_eps(symbol=symbol, start_date=start_date)
    except FetcherError as exc:
        st.info(f"EPS 資料暫時無法取得：{exc}")
        return
    except Exception as exc:  # noqa: BLE001
        st.warning(f"EPS 資料讀取失敗：{exc}")
        return

    display = _build_eps_display_table(eps_df=eps_df, end_year=end_year)
    if display.empty:
        st.info("此股票在近 15 年範圍內沒有可用 EPS 資料。")
        return

    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("年度 EPS 為已取得季度 EPS 加總，不補值、不推估。")


def _build_eps_display_table(*, eps_df: pd.DataFrame, end_year: int) -> pd.DataFrame:
    if eps_df is None or eps_df.empty:
        return pd.DataFrame(columns=["年度", "Q1 EPS", "Q2 EPS", "Q3 EPS", "Q4 EPS", "年度 EPS"])

    work = eps_df.copy()
    work["year"] = pd.to_numeric(work.get("year"), errors="coerce")
    work["quarter"] = pd.to_numeric(work.get("quarter"), errors="coerce")
    work["eps"] = pd.to_numeric(work.get("eps"), errors="coerce")
    work = work.dropna(subset=["year", "quarter", "eps"])
    if work.empty:
        return pd.DataFrame(columns=["年度", "Q1 EPS", "Q2 EPS", "Q3 EPS", "Q4 EPS", "年度 EPS"])

    work["year"] = work["year"].astype("int64")
    work["quarter"] = work["quarter"].astype("int64")
    work = work[work["quarter"].between(1, 4)].copy()
    work = work[work["year"].between(end_year - 14, end_year)].copy()
    if work.empty:
        return pd.DataFrame(columns=["年度", "Q1 EPS", "Q2 EPS", "Q3 EPS", "Q4 EPS", "年度 EPS"])

    pivot = work.pivot_table(index="year", columns="quarter", values="eps", aggfunc="last")
    pivot = pivot.reindex(columns=[1, 2, 3, 4]).sort_index(ascending=False)
    annual = pivot.sum(axis=1, min_count=1)

    display = pd.DataFrame(
        {
            "年度": pivot.index.astype("int64"),
            "Q1 EPS": pivot[1].map(_format_eps_value),
            "Q2 EPS": pivot[2].map(_format_eps_value),
            "Q3 EPS": pivot[3].map(_format_eps_value),
            "Q4 EPS": pivot[4].map(_format_eps_value),
            "年度 EPS": annual.map(_format_eps_value),
        }
    ).reset_index(drop=True)
    return display


def _format_eps_value(value: float) -> str:
    if pd.isna(value):
        return "尚無資料"
    return f"{float(value):.2f}"


def _as_taipei_start(value: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value).normalize()
    if ts.tzinfo is None:
        return ts.tz_localize(TAIPEI_TZ)
    return ts.tz_convert(TAIPEI_TZ)


if __name__ == "__main__":
    render()
