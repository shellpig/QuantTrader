"""Backtest page."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from src.backtest.engine_event import EventDrivenBacktester
from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.report import TearsheetReport
from src.core.constants import TAIPEI_TZ
from src.data.storage import ParquetStorage
from src.strategy.examples.ma_cross import MACrossStrategy

_TW_SYMBOL_PATTERN = re.compile(r"^\d{4,6}$")


def render() -> None:
    st.title("回測")
    st.caption("執行策略回測並顯示 Tearsheet 圖表。")

    today = pd.Timestamp.today().date()
    default_start = (pd.Timestamp.today() - pd.Timedelta(days=365 * 3)).date()

    c1, c2 = st.columns(2)
    with c1:
        symbol = st.text_input("股票代碼", value="2330").strip()
        start_date = st.date_input("開始日期", value=default_start)
    with c2:
        engine_name = st.selectbox("回測引擎", options=["向量化引擎", "事件驅動引擎"], index=0)
        end_date = st.date_input("結束日期", value=today)

    strategy_name = st.selectbox("策略", options=["MA Cross"], index=0)
    s1, s2 = st.columns(2)
    with s1:
        ma_short = int(st.number_input("MA 短週期", min_value=2, max_value=120, value=20, step=1))
    with s2:
        ma_long = int(st.number_input("MA 長週期", min_value=3, max_value=240, value=60, step=1))

    if st.button("執行回測", type="primary"):
        _run_backtest(
            symbol=symbol,
            start_date=pd.Timestamp(start_date),
            end_date=pd.Timestamp(end_date),
            engine_name=engine_name,
            strategy_name=strategy_name,
            ma_short=ma_short,
            ma_long=ma_long,
        )


def _run_backtest(
    *,
    symbol: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    engine_name: str,
    strategy_name: str,
    ma_short: int,
    ma_long: int,
) -> None:
    if not _TW_SYMBOL_PATTERN.fullmatch(symbol):
        st.error("請輸入有效的台股代碼（4~6 位數字）。")
        return
    start_ts = _as_taipei_start(start_date)
    end_exclusive = _as_taipei_start(end_date) + pd.Timedelta(days=1)

    if end_exclusive <= start_ts:
        st.error("結束日期不可早於開始日期。")
        return
    if ma_short >= ma_long:
        st.error("MA 短週期必須小於 MA 長週期。")
        return

    try:
        storage = ParquetStorage()
        df = storage.load_adjusted(symbol)
        if df.empty:
            df = storage.load_daily(symbol)
        if df.empty:
            st.warning(f"找不到 {symbol} 的本機資料，請先到「資料管理」更新。")
            return

        data = df.copy()
        data["date"] = pd.to_datetime(data["date"], errors="coerce")
        data = data.dropna(subset=["date"])
        if data["date"].dt.tz is None:
            data["date"] = data["date"].dt.tz_localize(TAIPEI_TZ)
        else:
            data["date"] = data["date"].dt.tz_convert(TAIPEI_TZ)
        data = data[(data["date"] >= start_ts) & (data["date"] < end_exclusive)].copy()
        if data.empty:
            st.warning("指定區間沒有可用資料。")
            return

        if strategy_name != "MA Cross":
            st.error(f"尚未支援策略：{strategy_name}")
            return
        strategy = MACrossStrategy(ma_short=ma_short, ma_long=ma_long)

        if engine_name == "向量化引擎":
            engine = VectorizedBacktester()
        else:
            engine = EventDrivenBacktester()

        result = engine.run(strategy=strategy, data=data)
        report = TearsheetReport(result)
        figures = report.get_streamlit_figures()

        m0, m1, m2, m3, m4 = st.columns(5)
        m0.metric("交易次數", f"{int(result.total_trades)}")
        m1.metric("總報酬", f"{result.total_return * 100:.2f}%")
        m2.metric("年化報酬", f"{result.annual_return * 100:.2f}%")
        m3.metric("最大回撤", f"{result.max_drawdown * 100:.2f}%")
        m4.metric("Sharpe", f"{result.sharpe_ratio:.2f}")

        st.plotly_chart(figures["equity"], use_container_width=True)
        st.plotly_chart(figures["drawdown"], use_container_width=True)
        st.plotly_chart(figures["monthly"], use_container_width=True)
        st.plotly_chart(figures["summary"], use_container_width=True)
    except Exception as exc:  # noqa: BLE001
        st.error(f"回測失敗：{exc}")


def _as_taipei_start(value: pd.Timestamp) -> pd.Timestamp:
    ts = pd.Timestamp(value).normalize()
    if ts.tzinfo is None:
        return ts.tz_localize(TAIPEI_TZ)
    return ts.tz_convert(TAIPEI_TZ)


if __name__ == "__main__":
    render()
