"""Data management page."""

from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.core.config import get_config
from src.core.market import get_market_spec, normalize_market, normalize_symbol
from src.data.cleaner import DataCleaner
from src.data.fetcher import FinMindFetcher, IDataFetcher, YFinanceFetcher
from src.data.maintenance import DataMaintenance
from src.data.storage import DuckDBMeta, ParquetStorage
from src.ui.stock_selector import render_stock_selector

_MARKET_OPTION_LABELS: tuple[str, str] = ("台股", "美股")
_MARKET_BY_LABEL: dict[str, str] = {"台股": "tw", "美股": "us"}


def render() -> None:
    st.title("資料管理")
    st.caption("管理本機歷史資料、更新與重建。")
    market = _render_market_selector("data_mgmt")
    _render_market_capabilities(market)

    symbol = _render_symbol_input(market)
    _render_optional_us_status(market=market, symbol=symbol)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        do_refresh = st.button("重新整理列表", width="stretch")
    with col2:
        do_update = st.button("更新", type="primary", width="stretch")
    with col3:
        do_rebuild = st.button("重建", width="stretch")

    if do_update or do_rebuild:
        try:
            normalized_symbol = normalize_symbol(symbol, market=market)
        except ValueError:
            if market == "tw":
                st.error("請輸入有效的台股代碼（4~6 位英數字，或從名稱搜尋結果選擇）。")
            else:
                st.error("請輸入有效的美股代碼（例如 AAPL、MSFT、SPY、BRK.B）。")
        else:
            _run_maintenance(symbol=normalized_symbol, rebuild=do_rebuild, market=market)

    if do_refresh or True:
        _render_meta_table(market=market)


def _render_optional_us_status(*, market: str, symbol: str) -> None:
    if normalize_market(market) != "us":
        return
    if not symbol:
        return
    try:
        normalized_symbol = normalize_symbol(symbol, market="us")
    except ValueError:
        return
    _render_us_data_status(normalized_symbol, ParquetStorage())


def _render_market_selector(key_prefix: str) -> str:
    label = st.selectbox("市場", options=list(_MARKET_OPTION_LABELS), index=0, key=f"{key_prefix}_market")
    return normalize_market(_MARKET_BY_LABEL.get(str(label), "tw"))


def _render_symbol_input(market: str) -> str:
    if market == "tw":
        return render_stock_selector("股票代碼或名稱", key_prefix="data_mgmt", market=market, default="2330")
    return render_stock_selector("美股代碼", key_prefix="data_mgmt", market=market, default="AAPL")


def _render_market_capabilities(market: str) -> None:
    normalized_market = normalize_market(market)
    if normalized_market != "us":
        return
    market_spec = get_market_spec(normalized_market)
    st.caption("美股模式：僅支援日 K 更新與重建。")
    st.caption(f"資料來源：yfinance　時區：{market_spec.timezone}")
    st.info("US-1 尚未支援美股分 K。")
    st.info("US-1 尚未支援美股籌碼資料。")


def _render_us_data_status(symbol: str, storage: ParquetStorage) -> None:
    raw = storage.load_daily(symbol, market="us")
    adjusted = storage.load_adjusted(symbol, market="us")
    rows = [
        _build_status_row("raw daily", raw),
        _build_status_row("adjusted daily", adjusted),
    ]
    st.caption("美股本機資料狀態")
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)


def _build_status_row(data_type: str, df: pd.DataFrame) -> dict[str, object]:
    if df.empty:
        return {
            "資料類型": data_type,
            "狀態": "尚無資料",
            "筆數": 0,
            "起始日": "-",
            "結束日": "-",
        }

    dates = pd.to_datetime(df.get("date"), errors="coerce").dropna()
    if dates.empty:
        start_date = "-"
        end_date = "-"
    else:
        start_date = dates.min().strftime("%Y-%m-%d")
        end_date = dates.max().strftime("%Y-%m-%d")

    return {
        "資料類型": data_type,
        "狀態": "可用",
        "筆數": int(len(df)),
        "起始日": start_date,
        "結束日": end_date,
    }


def _run_maintenance(symbol: str, rebuild: bool, market: str = "tw") -> None:
    normalized_market = normalize_market(market)
    progress = st.progress(0, text="準備中...")
    errors: list[str] = []
    try:
        progress.progress(10, text="初始化元件...")
        storage = ParquetStorage()
        fetchers = _build_fetchers_from_config(market=normalized_market)
        if not fetchers:
            raise RuntimeError("No available data source. Details: n/a")

        for source, fetcher in fetchers:
            meta = DuckDBMeta()
            try:
                maintenance = DataMaintenance(
                    fetcher=fetcher,
                    storage=storage,
                    meta=meta,
                    cleaner=DataCleaner(),
                )
                if rebuild:
                    progress.progress(40, text=f"重建 {symbol} 日K資料中...")
                    report = maintenance.rebuild_symbol(symbol, market=normalized_market)
                    progress.progress(100, text="完成")
                    st.success(f"{symbol} 重建完成（來源：{source}）。")
                    st.json(asdict(report), expanded=False)
                else:
                    progress.progress(40, text=f"更新 {symbol} 日K中...")
                    added = maintenance.update_daily(symbol, market=normalized_market)
                    progress.progress(100, text="完成")
                    st.success(f"{symbol} 更新完成，新增 {added} 筆（來源：{source}）。")
                return
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{source}: {exc}")
            finally:
                meta.close()
        raise RuntimeError(" | ".join(errors))
    except Exception as exc:  # noqa: BLE001
        st.error(f"資料操作失敗：{exc}")


def _render_meta_table(market: str = "tw") -> None:
    normalized_market = normalize_market(market)
    try:
        meta = DuckDBMeta()
        df = meta.list_all()
    except Exception as exc:  # noqa: BLE001
        st.error(f"讀取 metadata 失敗：{exc}")
        return
    finally:
        try:
            meta.close()  # type: ignore[name-defined]
        except Exception:
            pass

    if "market" in df.columns:
        df = df[df["market"] == normalized_market].copy()

    if df.empty:
        st.info("目前尚無資料。可輸入代碼後按「更新」下載。")
        return

    out = df.copy()
    for col in ("first_date", "last_date", "updated_at"):
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    st.dataframe(out, width="stretch")


def _build_fetcher() -> IDataFetcher:
    fetchers = _build_fetchers_from_config()
    if fetchers:
        return fetchers[0][1]
    raise RuntimeError("No available data source. Details: n/a")


def _build_fetchers_from_config(market: str = "tw") -> list[tuple[str, IDataFetcher]]:
    normalized_market = normalize_market(market)
    cfg = get_config()
    data_section = cfg.get("data", {}) if isinstance(cfg, dict) else {}
    if normalized_market == "us":
        order = ["yfinance"]
    else:
        primary = str(data_section.get("primary_source", "finmind")).strip().lower()
        fallback = str(data_section.get("fallback_source", "yfinance")).strip().lower()
        order = [primary, fallback]

    fetchers: list[tuple[str, IDataFetcher]] = []
    for source in order:
        if source in {name for name, _ in fetchers}:
            continue
        try:
            if source == "finmind":
                if normalized_market == "tw":
                    fetchers.append((source, FinMindFetcher()))
            if source == "yfinance":
                fetchers.append((source, YFinanceFetcher(market=normalized_market)))
        except Exception:  # noqa: BLE001
            continue
    return fetchers


if __name__ == "__main__":
    render()
