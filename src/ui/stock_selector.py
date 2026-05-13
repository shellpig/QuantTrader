"""Shared stock lookup widgets for Streamlit pages."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

import pandas as pd
import streamlit as st

from src.core.market import normalize_market, normalize_symbol
from src.data.fetcher import FinMindFetcher

_STOCK_OPTIONS_KEY = "tw_stock_options"
_STOCK_LOOKUP_ERROR_KEY = "tw_stock_lookup_error"
_TW_SYMBOL_PATTERN = re.compile(r"^[0-9A-Z]{4,6}$")
_US_SYMBOL_HINT = "AAPL / MSFT / SPY / BRK.B"


@dataclass(frozen=True)
class StockOption:
    symbol: str
    name: str


def normalize_stock_options(df: pd.DataFrame) -> list[StockOption]:
    if df.empty or "symbol" not in df.columns:
        return []
    out = df.copy()
    if "name" not in out.columns:
        out["name"] = ""
    out["symbol"] = out["symbol"].fillna("").astype(str).str.strip().str.upper()
    out["name"] = out["name"].fillna("").astype(str).str.strip()
    out = out[out["symbol"].str.fullmatch(_TW_SYMBOL_PATTERN.pattern)]
    out = out.drop_duplicates(subset=["symbol"], keep="first").sort_values("symbol")
    return [StockOption(symbol=row.symbol, name=row.name) for row in out.itertuples(index=False)]


def find_stock_matches(query: str, options: list[StockOption], *, limit: int = 20) -> list[StockOption]:
    normalized = str(query).strip().upper()
    if not normalized:
        return []
    exact = [opt for opt in options if opt.symbol == normalized or opt.name.upper() == normalized]
    partial = [
        opt for opt in options
        if opt not in exact and (normalized in opt.symbol or normalized in opt.name.upper())
    ]
    return (exact + partial)[:limit]


def format_stock_option(option: StockOption) -> str:
    return f"{option.name}（{option.symbol}）" if option.name else option.symbol


def render_stock_selector(
    label: str,
    *,
    key_prefix: str,
    market: str = "tw",
    default: str = "",
    text_input_kwargs: dict[str, Any] | None = None,
) -> str:
    normalized_market = normalize_market(market)
    if normalized_market == "us":
        raw = st.text_input(
            label,
            value=default,
            key=f"{key_prefix}_stock_query",
            placeholder=_US_SYMBOL_HINT,
            **(text_input_kwargs or {}),
        ).strip()
        if not raw:
            return ""
        try:
            return normalize_symbol(raw, market=normalized_market)
        except ValueError:
            return raw.upper()

    query = st.text_input(
        label,
        value=default,
        key=f"{key_prefix}_stock_query",
        **(text_input_kwargs or {}),
    ).strip()
    if not query:
        return ""

    normalized_query = query.strip().upper()
    if _TW_SYMBOL_PATTERN.fullmatch(normalized_query):
        return normalized_query

    matches = find_stock_matches(normalized_query, _get_cached_stock_options())
    if not matches:
        return normalized_query

    labels = [format_stock_option(option) for option in matches]
    selected_label = st.selectbox(
        "選擇股票",
        options=labels,
        index=0,
        key=f"{key_prefix}_stock_choice",
    )
    return matches[labels.index(selected_label)].symbol


def _get_cached_stock_options() -> list[StockOption]:
    cached = st.session_state.get(_STOCK_OPTIONS_KEY)
    if isinstance(cached, list):
        return cached

    try:
        options = normalize_stock_options(FinMindFetcher().fetch_stock_info())
    except Exception as exc:  # noqa: BLE001
        options = []
        st.session_state[_STOCK_LOOKUP_ERROR_KEY] = str(exc)
    st.session_state[_STOCK_OPTIONS_KEY] = options
    return options
