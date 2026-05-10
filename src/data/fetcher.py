"""Data fetchers for external market data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
import time
from typing import Any

import pandas as pd
import requests
import yfinance as yf

from src.core.config import get_config
from src.core.constants import (
    INSTITUTIONAL_COLUMNS,
    MARGIN_COLUMNS,
    SPLITS_COLUMNS,
    STANDARD_COLUMNS,
    TAIPEI_TZ,
)
from src.core.exceptions import FetcherError


def _empty_standard_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
            "open": pd.Series(dtype="float64"),
            "high": pd.Series(dtype="float64"),
            "low": pd.Series(dtype="float64"),
            "close": pd.Series(dtype="float64"),
            "volume": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[STANDARD_COLUMNS]


def _empty_dividends_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
            "cash_dividend": pd.Series(dtype="float64"),
            "stock_dividend": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[["date", "cash_dividend", "stock_dividend", "symbol"]]


def _empty_splits_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
            "before_price": pd.Series(dtype="float64"),
            "after_price": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[SPLITS_COLUMNS]


def _empty_eps_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": pd.Series(dtype="int64"),
            "quarter": pd.Series(dtype="int64"),
            "eps": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
            "report_date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
        }
    )[["year", "quarter", "eps", "symbol", "report_date"]]


def _empty_institutional_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
            "foreign_buy": pd.Series(dtype="int64"),
            "foreign_sell": pd.Series(dtype="int64"),
            "foreign_net": pd.Series(dtype="int64"),
            "trust_buy": pd.Series(dtype="int64"),
            "trust_sell": pd.Series(dtype="int64"),
            "trust_net": pd.Series(dtype="int64"),
            "dealer_buy": pd.Series(dtype="int64"),
            "dealer_sell": pd.Series(dtype="int64"),
            "dealer_net": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[INSTITUTIONAL_COLUMNS]


def _empty_margin_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {TAIPEI_TZ}]"),
            "margin_buy": pd.Series(dtype="int64"),
            "margin_sell": pd.Series(dtype="int64"),
            "margin_balance": pd.Series(dtype="int64"),
            "short_buy": pd.Series(dtype="int64"),
            "short_sell": pd.Series(dtype="int64"),
            "short_balance": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[MARGIN_COLUMNS]


def localize_to_taipei(df: pd.DataFrame, col: str = "date") -> pd.DataFrame:
    """
    Standardize datetime column to Asia/Taipei.

    If source datetimes are naive, they are localized to Asia/Taipei.
    If source datetimes are timezone-aware, they are converted to Asia/Taipei.
    """
    target_dtype = f"datetime64[ns, {TAIPEI_TZ}]"

    if col not in df.columns:
        raise FetcherError(f"Missing required datetime column: {col}")

    if df.empty:
        out = df.copy()
        out[col] = pd.Series(dtype=target_dtype)
        return out

    out = df.copy()
    series = pd.to_datetime(out[col], errors="coerce")

    if series.dt.tz is None:
        out[col] = series.dt.tz_localize(TAIPEI_TZ)
    else:
        out[col] = series.dt.tz_convert(TAIPEI_TZ)
    out[col] = out[col].astype(target_dtype)
    return out


def _finalize_schema(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        return _empty_standard_dataframe()

    out = df.copy()

    for col in STANDARD_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_standard_dataframe()

    out = localize_to_taipei(out, col="date")

    for price_col in ("open", "high", "low", "close"):
        out[price_col] = pd.to_numeric(out[price_col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close"]).copy()
    if out.empty:
        return _empty_standard_dataframe()

    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype("int64")
    out["open"] = out["open"].astype("float64")
    out["high"] = out["high"].astype("float64")
    out["low"] = out["low"].astype("float64")
    out["close"] = out["close"].astype("float64")

    out = out[STANDARD_COLUMNS].sort_values("date").reset_index(drop=True)
    return out


class IDataFetcher(ABC):
    """Abstract interface for all fetchers."""

    @abstractmethod
    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily bars."""

    @abstractmethod
    def fetch_minute(self, symbol: str, start: str, end: str, freq: str = "1") -> pd.DataFrame:
        """Fetch minute bars."""


class FinMindFetcher(IDataFetcher):
    """FinMind data source fetcher."""

    BASE_URL = "https://api.finmindtrade.com/api/v4/data"
    VALID_MINUTE_FREQ = {"1", "5", "15", "30", "60"}

    def __init__(
        self,
        token: str | None = None,
        session: requests.Session | None = None,
        retries: int = 3,
        timeout_seconds: int = 20,
    ):
        if token is None:
            config = get_config()
            secrets = config.get("secrets", {})
            if isinstance(secrets, dict):
                token = str(secrets.get("finmind_token", "")).strip()
            else:
                token = ""

        if not token:
            raise FetcherError("FINMIND_TOKEN is required for FinMindFetcher.")

        self._token = token
        self._session = session or requests.Session()
        self._retries = max(1, retries)
        self._timeout_seconds = timeout_seconds

    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        raw = self._request_data(
            {
                "dataset": "TaiwanStockPrice",
                "data_id": symbol,
                "start_date": start,
                "end_date": end,
            }
        )
        return self._normalize_finmind(raw, symbol=symbol)

    def fetch_minute(self, symbol: str, start: str, end: str, freq: str = "1") -> pd.DataFrame:
        if freq not in self.VALID_MINUTE_FREQ:
            raise ValueError(f"Unsupported minute frequency: {freq}")

        raw = self._request_data(
            {
                "dataset": "TaiwanStockPriceMinute",
                "data_id": symbol,
                "start_date": start,
                "end_date": end,
                "timeframe": freq,
            }
        )
        return self._normalize_finmind(raw, symbol=symbol)

    def fetch_dividends(self, symbol: str, start_date: str = "2000-01-01") -> pd.DataFrame:
        """
        Fetch Taiwan stock dividend events from FinMind.

        Returns columns:
        - date: ex-dividend trading date (tz-aware Asia/Taipei)
        - cash_dividend: cash dividend (NTD/share)
        - stock_dividend: stock dividend (NTD/share, ratio * 10)
        - symbol: stock id
        """
        raw = self._request_data(
            {
                "dataset": "TaiwanStockDividend",
                "data_id": symbol,
                "start_date": start_date,
            }
        )
        return self._normalize_dividends(raw, symbol=symbol)

    def fetch_eps(self, symbol: str, start_date: str = "2000-01-01") -> pd.DataFrame:
        """
        Fetch EPS records from FinMind financial statements dataset.

        Returns columns:
        - year: fiscal year
        - quarter: 1-4
        - eps: EPS value
        - symbol: stock id
        - report_date: source report date (tz-aware Asia/Taipei)
        """
        raw = self._request_data(
            {
                "dataset": "TaiwanStockFinancialStatements",
                "data_id": symbol,
                "start_date": start_date,
            }
        )
        return self._normalize_eps(raw, symbol=symbol)

    def fetch_splits(self, symbol: str, start_date: str = "2000-01-01") -> pd.DataFrame:
        """
        Fetch Taiwan stock split events from FinMind.

        Returns columns:
        - date: split trading date (tz-aware Asia/Taipei)
        - before_price: theoretical pre-split reference price
        - after_price: post-split reference/opening price
        - symbol: stock id
        """
        raw = self._request_data(
            {
                "dataset": "TaiwanStockSplitPrice",
                "data_id": symbol,
                "start_date": start_date,
            }
        )
        return self._normalize_splits(raw, symbol=symbol)

    def fetch_institutional(self, symbol: str, start_date: str) -> pd.DataFrame:
        """
        Fetch institutional buy/sell data and normalize to wide format.

        Returned unit is shares (股).
        """
        raw = self._request_data(
            {
                "dataset": "TaiwanStockInstitutionalInvestorsBuySell",
                "data_id": symbol,
                "start_date": start_date,
            }
        )
        return self._normalize_institutional(raw, symbol=symbol)

    def fetch_margin(self, symbol: str, start_date: str) -> pd.DataFrame:
        """
        Fetch margin/short data and normalize to canonical schema.

        Returned unit is lots (張).
        """
        raw = self._request_data(
            {
                "dataset": "TaiwanStockMarginPurchaseShortSale",
                "data_id": symbol,
                "start_date": start_date,
            }
        )
        return self._normalize_margin(raw, symbol=symbol)

    def fetch_institutional_incremental(
        self,
        symbol: str,
        storage: Any,
        *,
        default_start_date: str = "2000-01-01",
    ) -> pd.DataFrame:
        existing = storage.load_institutional(symbol)
        if existing.empty:
            start_date = default_start_date
        else:
            last_date = pd.to_datetime(existing["date"], errors="coerce").max()
            if pd.isna(last_date):
                start_date = default_start_date
            else:
                start_date = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        incoming = self.fetch_institutional(symbol, start_date)
        merged = pd.concat([existing, incoming], ignore_index=True)
        merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
        merged = merged.dropna(subset=["date"]).drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)
        storage.save_institutional(symbol, merged)
        return merged

    def fetch_margin_incremental(
        self,
        symbol: str,
        storage: Any,
        *,
        default_start_date: str = "2000-01-01",
    ) -> pd.DataFrame:
        existing = storage.load_margin(symbol)
        if existing.empty:
            start_date = default_start_date
        else:
            last_date = pd.to_datetime(existing["date"], errors="coerce").max()
            if pd.isna(last_date):
                start_date = default_start_date
            else:
                start_date = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        incoming = self.fetch_margin(symbol, start_date)
        merged = pd.concat([existing, incoming], ignore_index=True)
        merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
        merged = merged.dropna(subset=["date"]).drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)
        storage.save_margin(symbol, merged)
        return merged

    def _request_data(self, params: dict[str, Any]) -> pd.DataFrame:
        headers = {"Authorization": f"Bearer {self._token}"}
        last_error: Exception | None = None

        for attempt in range(1, self._retries + 1):
            try:
                response = self._session.get(
                    self.BASE_URL,
                    params=params,
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                data = payload.get("data", [])
                if not isinstance(data, list):
                    raise FetcherError("Unexpected FinMind payload structure: data is not a list.")
                return pd.DataFrame(data)
            except (requests.RequestException, ValueError, FetcherError) as exc:
                last_error = exc
                if attempt < self._retries:
                    time.sleep(2 ** (attempt - 1))

        raise FetcherError(f"FinMind request failed after {self._retries} attempts.") from last_error

    def _normalize_finmind(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_standard_dataframe()

        mapped = raw.rename(
            columns={
                "date": "date",
                "open": "open",
                "max": "high",
                "min": "low",
                "close": "close",
                "Trading_Volume": "volume",
                "stock_id": "symbol",
            }
        )
        return _finalize_schema(mapped, symbol=symbol)

    def _normalize_dividends(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_dividends_dataframe()

        out = raw.copy()
        for col in (
            "CashExDividendTradingDate",
            "StockExDividendTradingDate",
            "date",
            "CashEarningsDistribution",
            "CashStatutorySurplus",
            "StockEarningsDistribution",
            "StockStatutorySurplus",
            "stock_id",
        ):
            if col not in out.columns:
                out[col] = pd.NA

        ex_date_series = out[["CashExDividendTradingDate", "StockExDividendTradingDate", "date"]].bfill(axis=1).iloc[:, 0]
        normalized = pd.DataFrame(
            {
                "date": ex_date_series,
                "cash_dividend": pd.to_numeric(out["CashEarningsDistribution"], errors="coerce").fillna(0.0)
                + pd.to_numeric(out["CashStatutorySurplus"], errors="coerce").fillna(0.0),
                "stock_dividend": pd.to_numeric(out["StockEarningsDistribution"], errors="coerce").fillna(0.0)
                + pd.to_numeric(out["StockStatutorySurplus"], errors="coerce").fillna(0.0),
                "symbol": out["stock_id"].fillna(symbol).astype(str),
            }
        )
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        normalized = normalized.dropna(subset=["date"]).copy()
        if normalized.empty:
            return _empty_dividends_dataframe()

        normalized = localize_to_taipei(normalized, col="date")
        normalized["cash_dividend"] = normalized["cash_dividend"].astype("float64")
        normalized["stock_dividend"] = normalized["stock_dividend"].astype("float64")
        normalized = normalized[["date", "cash_dividend", "stock_dividend", "symbol"]]
        normalized = normalized.sort_values("date").drop_duplicates(subset=["date", "symbol"], keep="last").reset_index(drop=True)
        return normalized

    def _normalize_eps(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_eps_dataframe()

        out = raw.copy()
        for col in (
            "stock_id",
            "date",
            "type",
            "origin_name",
            "name",
            "item",
            "title",
            "value",
            "eps",
            "EPS",
            "year",
            "fiscal_year",
            "season",
            "quarter",
            "fiscal_quarter",
        ):
            if col not in out.columns:
                out[col] = pd.NA

        metric_label = out[["type", "origin_name", "name", "item", "title"]].bfill(axis=1).iloc[:, 0].astype(str)
        metric_mask = metric_label.str.contains("EPS", case=False, na=False) | metric_label.str.contains("每股", na=False)
        filtered = out[metric_mask].copy()
        if filtered.empty:
            return _empty_eps_dataframe()

        metric_label = metric_label.loc[filtered.index]
        report_date = pd.to_datetime(filtered["date"], errors="coerce")
        valid_report_dates = report_date.dropna()
        if valid_report_dates.empty:
            report_date = pd.Series(pd.NaT, index=filtered.index, dtype=f"datetime64[ns, {TAIPEI_TZ}]")
        elif valid_report_dates.dt.tz is None:
            report_date = report_date.dt.tz_localize(TAIPEI_TZ)
        else:
            report_date = report_date.dt.tz_convert(TAIPEI_TZ)

        year = pd.to_numeric(filtered["year"], errors="coerce")
        year = year.where(~year.isna(), pd.to_numeric(filtered["fiscal_year"], errors="coerce"))
        year = year.where(~year.isna(), report_date.dt.year if hasattr(report_date, "dt") else pd.Series(dtype="float64"))

        quarter_raw = filtered[["quarter", "season", "fiscal_quarter"]].bfill(axis=1).iloc[:, 0]
        quarter = quarter_raw.map(_parse_quarter_value)
        if hasattr(report_date, "dt"):
            quarter_from_date = ((report_date.dt.month - 1) // 3 + 1).astype("float64")
            quarter = quarter.where(~quarter.isna(), quarter_from_date)

        eps = pd.to_numeric(filtered["value"], errors="coerce")
        eps = eps.where(~eps.isna(), pd.to_numeric(filtered["eps"], errors="coerce"))
        eps = eps.where(~eps.isna(), pd.to_numeric(filtered["EPS"], errors="coerce"))

        normalized = pd.DataFrame(
            {
                "year": year,
                "quarter": quarter,
                "eps": eps,
                "symbol": filtered["stock_id"].fillna(symbol).astype(str),
                "report_date": report_date,
                "priority": metric_label.map(_eps_metric_priority),
            }
        )
        normalized = normalized.dropna(subset=["year", "quarter", "eps"]).copy()
        if normalized.empty:
            return _empty_eps_dataframe()

        normalized["year"] = normalized["year"].astype("int64")
        normalized["quarter"] = normalized["quarter"].astype("int64")
        normalized = normalized[normalized["quarter"].between(1, 4)].copy()
        if normalized.empty:
            return _empty_eps_dataframe()

        normalized["eps"] = normalized["eps"].astype("float64")
        normalized = normalized.sort_values(
            ["year", "quarter", "priority", "report_date"],
            ascending=[True, True, True, False],
        )
        normalized = normalized.drop_duplicates(subset=["year", "quarter", "symbol"], keep="first")
        normalized = normalized.sort_values(["year", "quarter"]).reset_index(drop=True)
        return normalized[["year", "quarter", "eps", "symbol", "report_date"]]

    def _normalize_splits(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_splits_dataframe()

        out = raw.copy()
        for col in ("date", "before_price", "after_price", "stock_id"):
            if col not in out.columns:
                out[col] = pd.NA

        normalized = pd.DataFrame(
            {
                "date": out["date"],
                "before_price": pd.to_numeric(out["before_price"], errors="coerce"),
                "after_price": pd.to_numeric(out["after_price"], errors="coerce"),
                "symbol": out["stock_id"].fillna(symbol).astype(str),
            }
        )
        normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce")
        normalized = normalized.dropna(subset=["date", "before_price", "after_price"]).copy()
        if normalized.empty:
            return _empty_splits_dataframe()

        normalized = normalized[
            (normalized["before_price"] > 0) & (normalized["after_price"] > 0)
        ].copy()
        if normalized.empty:
            return _empty_splits_dataframe()

        normalized = localize_to_taipei(normalized, col="date")
        normalized["before_price"] = normalized["before_price"].astype("float64")
        normalized["after_price"] = normalized["after_price"].astype("float64")
        normalized = normalized[SPLITS_COLUMNS]
        normalized = normalized.sort_values("date").drop_duplicates(subset=["date", "symbol"], keep="last").reset_index(drop=True)
        return normalized

    def _normalize_institutional(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_institutional_dataframe()

        out = raw.copy()
        for col in ("date", "name", "buy", "sell", "stock_id"):
            if col not in out.columns:
                out[col] = pd.NA

        out["buy"] = pd.to_numeric(out["buy"], errors="coerce").fillna(0).astype("int64")
        out["sell"] = pd.to_numeric(out["sell"], errors="coerce").fillna(0).astype("int64")
        out["net"] = out["buy"] - out["sell"]
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).copy()
        if out.empty:
            return _empty_institutional_dataframe()

        out["symbol"] = out["stock_id"].fillna(symbol).astype(str)
        out["category"] = out["name"].map(_institutional_name_to_category)
        out = out[out["category"].notna()].copy()
        if out.empty:
            return _empty_institutional_dataframe()

        grouped = (
            out.groupby(["date", "symbol", "category"], as_index=False)[["buy", "sell", "net"]]
            .sum()
            .reset_index(drop=True)
        )

        wide = grouped.pivot_table(
            index=["date", "symbol"],
            columns="category",
            values=["buy", "sell", "net"],
            aggfunc="sum",
            fill_value=0,
        )
        wide.columns = [f"{cat}_{metric}" for metric, cat in wide.columns]
        wide = wide.reset_index()

        normalized = pd.DataFrame(
            {
                "date": wide["date"],
                "foreign_buy": wide.get("foreign_buy", 0),
                "foreign_sell": wide.get("foreign_sell", 0),
                "foreign_net": wide.get("foreign_net", 0),
                "trust_buy": wide.get("trust_buy", 0),
                "trust_sell": wide.get("trust_sell", 0),
                "trust_net": wide.get("trust_net", 0),
                "dealer_buy": wide.get("dealer_buy", 0),
                "dealer_sell": wide.get("dealer_sell", 0),
                "dealer_net": wide.get("dealer_net", 0),
                "symbol": wide["symbol"],
            }
        )
        normalized = localize_to_taipei(normalized, col="date")
        for col in INSTITUTIONAL_COLUMNS:
            if col in {"date", "symbol"}:
                continue
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce").fillna(0).astype("int64")
        normalized = normalized[INSTITUTIONAL_COLUMNS]
        normalized = normalized.sort_values("date").drop_duplicates(subset=["date", "symbol"], keep="last").reset_index(drop=True)
        return normalized

    def _normalize_margin(self, raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
        if raw.empty:
            return _empty_margin_dataframe()

        out = raw.copy()
        field_map = {
            "date": "date",
            "stock_id": "symbol",
            "MarginPurchaseBuy": "margin_buy",
            "MarginPurchaseSell": "margin_sell",
            "MarginPurchaseTodayBalance": "margin_balance",
            "ShortSaleBuy": "short_buy",
            "ShortSaleSell": "short_sell",
            "ShortSaleTodayBalance": "short_balance",
        }
        out = out.rename(columns=field_map)
        for col in MARGIN_COLUMNS:
            if col not in out.columns:
                out[col] = pd.NA

        out["symbol"] = out["symbol"].fillna(symbol).astype(str)
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out = out.dropna(subset=["date"]).copy()
        if out.empty:
            return _empty_margin_dataframe()

        normalized = out[MARGIN_COLUMNS].copy()
        normalized = localize_to_taipei(normalized, col="date")
        for col in MARGIN_COLUMNS:
            if col in {"date", "symbol"}:
                continue
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce").fillna(0).astype("int64")
        normalized = normalized.sort_values("date").drop_duplicates(subset=["date", "symbol"], keep="last").reset_index(drop=True)
        return normalized


def _parse_quarter_value(value: Any) -> float:
    if pd.isna(value):
        return float("nan")
    text = str(value).strip().upper()
    if not text:
        return float("nan")
    if text.startswith("Q") and text[1:].isdigit():
        return float(int(text[1:]))
    if text.endswith("Q") and text[:-1].isdigit():
        return float(int(text[:-1]))
    if text.isdigit():
        return float(int(text))
    if "第一季" in text:
        return 1.0
    if "第二季" in text:
        return 2.0
    if "第三季" in text:
        return 3.0
    if "第四季" in text:
        return 4.0
    return float("nan")


def _eps_metric_priority(label: str) -> int:
    label_text = str(label or "")
    name = label_text.upper()
    if "基本每股盈餘" in label_text or "BASIC EPS" in name or "BASICEPS" in name:
        return 0
    if "稀釋" in label_text or "DILUTED" in name:
        return 2
    return 1


def _institutional_name_to_category(name: Any) -> str | None:
    label = str(name or "").strip()
    if label in {"Foreign_Investor", "Foreign_Dealer_Self"}:
        return "foreign"
    if label == "Investment_Trust":
        return "trust"
    if label in {"Dealer_self", "Dealer_Hedging"}:
        return "dealer"
    return None


class YFinanceFetcher(IDataFetcher):
    """yfinance backup source fetcher."""

    VALID_MINUTE_FREQ = {"1", "5", "15", "30", "60"}

    def __init__(self, downloader: Callable[..., pd.DataFrame] | None = None):
        self._downloader = downloader or yf.download

    def fetch_daily(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        ticker = f"{symbol}.TW"
        try:
            raw = self._downloader(
                ticker,
                start=start,
                end=end,
                interval="1d",
                auto_adjust=False,
                progress=False,
                group_by="column",
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise FetcherError(f"yfinance download failed for {ticker}") from exc

        return self._normalize_yfinance(raw, symbol=symbol)

    def fetch_minute(self, symbol: str, start: str, end: str, freq: str = "1") -> pd.DataFrame:
        if freq not in self.VALID_MINUTE_FREQ:
            raise ValueError(f"Unsupported minute frequency: {freq}")

        interval_map = {"1": "1m", "5": "5m", "15": "15m", "30": "30m", "60": "60m"}
        ticker = f"{symbol}.TW"
        try:
            raw = self._downloader(
                ticker,
                start=start,
                end=end,
                interval=interval_map[freq],
                auto_adjust=False,
                progress=False,
                group_by="column",
                threads=False,
            )
        except Exception as exc:  # noqa: BLE001 - normalize provider errors
            raise FetcherError(f"yfinance download failed for {ticker}") from exc

        return self._normalize_yfinance(raw, symbol=symbol)

    def _normalize_yfinance(self, raw: pd.DataFrame | None, symbol: str) -> pd.DataFrame:
        if raw is None or raw.empty:
            return _empty_standard_dataframe()

        normalized = raw.copy()
        if isinstance(normalized.columns, pd.MultiIndex):
            normalized.columns = normalized.columns.get_level_values(0)

        normalized = normalized.reset_index()
        date_col = normalized.columns[0]
        mapped = normalized.rename(
            columns={
                date_col: "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        mapped["symbol"] = symbol
        return _finalize_schema(mapped, symbol=symbol)
