"""Parquet and DuckDB storage utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.core.config import get_data_dir
from src.core.constants import (
    DIVIDENDS_COLUMNS,
    EPS_COLUMNS,
    INSTITUTIONAL_COLUMNS,
    MARGIN_COLUMNS,
    MONTHLY_REVENUE_COLUMNS,
    PER_COLUMNS,
    SPLITS_COLUMNS,
    STANDARD_COLUMNS,
)
from src.core.exceptions import StorageError
from src.core.market import get_market_spec, normalize_market, validate_symbol


def _empty_standard_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "open": pd.Series(dtype="float64"),
            "high": pd.Series(dtype="float64"),
            "low": pd.Series(dtype="float64"),
            "close": pd.Series(dtype="float64"),
            "volume": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[STANDARD_COLUMNS]


def _empty_splits_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "before_price": pd.Series(dtype="float64"),
            "after_price": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[SPLITS_COLUMNS]


def _empty_institutional_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
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


def _empty_margin_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "margin_buy": pd.Series(dtype="int64"),
            "margin_sell": pd.Series(dtype="int64"),
            "margin_balance": pd.Series(dtype="int64"),
            "short_buy": pd.Series(dtype="int64"),
            "short_sell": pd.Series(dtype="int64"),
            "short_balance": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[MARGIN_COLUMNS]


def _empty_dividends_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "cash_dividend": pd.Series(dtype="float64"),
            "stock_dividend": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[DIVIDENDS_COLUMNS]


def _empty_eps_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "year": pd.Series(dtype="int64"),
            "quarter": pd.Series(dtype="int64"),
            "eps": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
            "report_date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
        }
    )[[*EPS_COLUMNS, "report_date"]]


def _empty_per_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "per": pd.Series(dtype="float64"),
            "pbr": pd.Series(dtype="float64"),
            "dividend_yield": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[PER_COLUMNS]


def _empty_monthly_revenue_dataframe(timezone: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype=f"datetime64[ns, {timezone}]"),
            "revenue": pd.Series(dtype="float64"),
            "revenue_month": pd.Series(dtype="int64"),
            "revenue_year": pd.Series(dtype="int64"),
            "symbol": pd.Series(dtype="object"),
        }
    )[MONTHLY_REVENUE_COLUMNS]


def _normalize_market_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_standard_dataframe(timezone)

    out = df.copy()
    for col in STANDARD_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_standard_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")

    for price_col in ("open", "high", "low", "close"):
        out[price_col] = pd.to_numeric(out[price_col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close"]).copy()
    if out.empty:
        return _empty_standard_dataframe(timezone)

    out["open"] = out["open"].astype("float64")
    out["high"] = out["high"].astype("float64")
    out["low"] = out["low"].astype("float64")
    out["close"] = out["close"].astype("float64")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype("int64")

    return out[STANDARD_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_splits_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_splits_dataframe(timezone)

    out = df.copy()
    for col in SPLITS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["before_price"] = pd.to_numeric(out["before_price"], errors="coerce")
    out["after_price"] = pd.to_numeric(out["after_price"], errors="coerce")
    out = out.dropna(subset=["date", "before_price", "after_price"]).copy()
    if out.empty:
        return _empty_splits_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")

    out = out[(out["before_price"] > 0) & (out["after_price"] > 0)].copy()
    if out.empty:
        return _empty_splits_dataframe(timezone)

    out["before_price"] = out["before_price"].astype("float64")
    out["after_price"] = out["after_price"].astype("float64")
    return out[SPLITS_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_institutional_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_institutional_dataframe(timezone)

    out = df.copy()
    for col in INSTITUTIONAL_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_institutional_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")

    for col in INSTITUTIONAL_COLUMNS:
        if col in {"date", "symbol"}:
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype("int64")

    return out[INSTITUTIONAL_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_margin_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_margin_dataframe(timezone)

    out = df.copy()
    for col in MARGIN_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_margin_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")

    for col in MARGIN_COLUMNS:
        if col in {"date", "symbol"}:
            continue
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype("int64")

    return out[MARGIN_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_dividends_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_dividends_dataframe(timezone)

    out = df.copy()
    for col in DIVIDENDS_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["cash_dividend"] = pd.to_numeric(out["cash_dividend"], errors="coerce")
    out["stock_dividend"] = pd.to_numeric(out["stock_dividend"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_dividends_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")
    out["cash_dividend"] = out["cash_dividend"].fillna(0.0).astype("float64")
    out["stock_dividend"] = out["stock_dividend"].fillna(0.0).astype("float64")
    return out[DIVIDENDS_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_eps_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_eps_dataframe(timezone)

    out = df.copy()
    if "date" not in out.columns and "report_date" in out.columns:
        out["date"] = out["report_date"]

    for col in [*EPS_COLUMNS, "report_date"]:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["report_date"] = pd.to_datetime(out["report_date"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["quarter"] = pd.to_numeric(out["quarter"], errors="coerce")
    out["eps"] = pd.to_numeric(out["eps"], errors="coerce")
    out = out.dropna(subset=["date", "year", "quarter", "eps"]).copy()
    if out.empty:
        return _empty_eps_dataframe(timezone)

    for col in ("date", "report_date"):
        series = out[col]
        if series.dropna().empty:
            out[col] = pd.Series(pd.NaT, index=out.index, dtype=f"datetime64[ns, {timezone}]")
            continue
        if series.dt.tz is None:
            out[col] = series.dt.tz_localize(timezone)
        else:
            out[col] = series.dt.tz_convert(timezone)
        out[col] = out[col].astype(f"datetime64[ns, {timezone}]")

    out["year"] = out["year"].astype("int64")
    out["quarter"] = out["quarter"].astype("int64")
    out["eps"] = out["eps"].astype("float64")
    out = out[[*EPS_COLUMNS, "report_date"]].sort_values(["date", "year", "quarter"]).reset_index(drop=True)
    return out


def _normalize_per_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_per_dataframe(timezone)

    out = df.copy()
    for col in PER_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["per"] = pd.to_numeric(out["per"], errors="coerce")
    out["pbr"] = pd.to_numeric(out["pbr"], errors="coerce")
    out["dividend_yield"] = pd.to_numeric(out["dividend_yield"], errors="coerce")
    out = out.dropna(subset=["date"]).copy()
    if out.empty:
        return _empty_per_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")
    out["per"] = out["per"].astype("float64")
    out["pbr"] = out["pbr"].astype("float64")
    out["dividend_yield"] = out["dividend_yield"].astype("float64")
    return out[PER_COLUMNS].sort_values("date").reset_index(drop=True)


def _normalize_monthly_revenue_df(df: pd.DataFrame, symbol: str, timezone: str) -> pd.DataFrame:
    if df.empty:
        return _empty_monthly_revenue_dataframe(timezone)

    out = df.copy()
    for col in MONTHLY_REVENUE_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    out["symbol"] = out["symbol"].fillna(symbol).astype(str)
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out["revenue"] = pd.to_numeric(out["revenue"], errors="coerce")
    out["revenue_month"] = pd.to_numeric(out["revenue_month"], errors="coerce")
    out["revenue_year"] = pd.to_numeric(out["revenue_year"], errors="coerce")
    out = out.dropna(subset=["date", "revenue_month", "revenue_year"]).copy()
    if out.empty:
        return _empty_monthly_revenue_dataframe(timezone)

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(timezone)
    else:
        out["date"] = series.dt.tz_convert(timezone)
    out["date"] = out["date"].astype(f"datetime64[ns, {timezone}]")
    out["revenue"] = out["revenue"].astype("float64")
    out["revenue_month"] = out["revenue_month"].astype("int64")
    out["revenue_year"] = out["revenue_year"].astype("int64")
    return out[MONTHLY_REVENUE_COLUMNS].sort_values("date").reset_index(drop=True)


class ParquetStorage:
    """
    Parquet file storage with upsert behavior for market data.

    Paths:
    - daily: data/raw/tw/{symbol}/daily.parquet
    - minute: data/raw/tw/{symbol}/minute.parquet
    - adjusted: data/processed/tw/{symbol}/adj_daily.parquet
    """

    def __init__(self, data_dir: Path | None = None):
        self.data_dir = (data_dir or get_data_dir()).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _validate_market(self, market: str | None) -> str:
        try:
            return normalize_market(market)
        except ValueError as exc:
            raise StorageError(f"Unsupported market: {market}") from exc

    def _validate_symbol(self, symbol: str, market: str = "tw") -> str:
        try:
            return validate_symbol(symbol=symbol, market=market)
        except ValueError as exc:
            raise StorageError(str(exc)) from exc

    def _market_timezone(self, market: str) -> str:
        return get_market_spec(market).timezone

    def _build_market_path(self, layer: str, market: str, symbol: str, filename: str) -> Path:
        path = (self.data_dir / layer / market / symbol / filename).resolve(strict=False)
        try:
            path.relative_to(self.data_dir)
        except ValueError as exc:
            raise StorageError(f"Resolved path escapes data_dir: {path}") from exc
        return path

    def _daily_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "daily.parquet",
        )

    def _minute_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "minute.parquet",
        )

    def _adjusted_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "processed",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "adj_daily.parquet",
        )

    def _splits_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "splits.parquet",
        )

    def _institutional_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "institutional.parquet",
        )

    def _margin_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "margin.parquet",
        )

    def _per_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "per.parquet",
        )

    def _monthly_revenue_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "monthly_revenue.parquet",
        )

    def _dividends_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "dividends.parquet",
        )

    def _eps_path(self, symbol: str, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        return self._build_market_path(
            "raw",
            normalized_market,
            self._validate_symbol(symbol, normalized_market),
            "eps.parquet",
        )

    def _save_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_market_df(df, symbol, timezone=timezone)

        if path.exists():
            existing = self._load_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming

        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)

        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_standard_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_market_df(loaded, symbol=symbol, timezone=timezone)

    def _save_splits_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_splits_df(df, symbol, timezone=timezone)

        if path.exists():
            existing = self._load_splits_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming

        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)

        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_splits_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_splits_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_splits_df(loaded, symbol=symbol, timezone=timezone)

    def _save_institutional_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_institutional_df(df, symbol, timezone=timezone)

        if path.exists():
            existing = self._load_institutional_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming

        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_institutional_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_institutional_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_institutional_df(loaded, symbol=symbol, timezone=timezone)

    def _save_margin_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_margin_df(df, symbol, timezone=timezone)

        if path.exists():
            existing = self._load_margin_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming

        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last")
        merged = merged.sort_values("date").reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_margin_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_margin_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_margin_df(loaded, symbol=symbol, timezone=timezone)

    def _save_per_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_per_df(df, symbol, timezone=timezone)
        if path.exists():
            existing = self._load_per_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming
        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last").sort_values("date").reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_per_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_per_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_per_df(loaded, symbol=symbol, timezone=timezone)

    def _save_monthly_revenue_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_monthly_revenue_df(df, symbol, timezone=timezone)
        if path.exists():
            existing = self._load_monthly_revenue_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming
        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last").sort_values("date").reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_monthly_revenue_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_monthly_revenue_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_monthly_revenue_df(loaded, symbol=symbol, timezone=timezone)

    def _save_dividends_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_dividends_df(df, symbol, timezone=timezone)
        if path.exists():
            existing = self._load_dividends_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming
        merged = merged.drop_duplicates(subset=["date", "symbol"], keep="last").sort_values("date").reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_dividends_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_dividends_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_dividends_df(loaded, symbol=symbol, timezone=timezone)

    def _save_eps_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame, timezone: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_eps_df(df, symbol, timezone=timezone)
        if path.exists():
            existing = self._load_eps_or_empty(path, symbol, timezone=timezone)
            merged = pd.concat([existing, incoming], ignore_index=True)
        else:
            merged = incoming
        merged = merged.drop_duplicates(subset=["date", "year", "quarter", "symbol"], keep="last")
        merged = merged.sort_values(["date", "year", "quarter"]).reset_index(drop=True)
        try:
            merged.to_parquet(path, index=False)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to write parquet: {path}") from exc
        return path

    def _load_eps_or_empty(self, path: Path, symbol: str, timezone: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_eps_dataframe(timezone)
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_eps_df(loaded, symbol=symbol, timezone=timezone)

    def save_daily(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_with_upsert(
            self._daily_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_or_empty(
            self._daily_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_minute(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_with_upsert(
            self._minute_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_minute(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_or_empty(
            self._minute_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_adjusted(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_with_upsert(
            self._adjusted_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_or_empty(
            self._adjusted_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_splits(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_splits_with_upsert(
            self._splits_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_splits(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_splits_or_empty(
            self._splits_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_institutional(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_institutional_with_upsert(
            self._institutional_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_institutional(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_institutional_or_empty(
            self._institutional_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_margin(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_margin_with_upsert(
            self._margin_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_margin(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_margin_or_empty(
            self._margin_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_per(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_per_with_upsert(
            self._per_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_per(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_per_or_empty(
            self._per_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_monthly_revenue(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_monthly_revenue_with_upsert(
            self._monthly_revenue_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_monthly_revenue(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_monthly_revenue_or_empty(
            self._monthly_revenue_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_dividends(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_dividends_with_upsert(
            self._dividends_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_dividends(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_dividends_or_empty(
            self._dividends_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )

    def save_eps(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._save_eps_with_upsert(
            self._eps_path(normalized_symbol, normalized_market),
            normalized_symbol,
            df,
            timezone=self._market_timezone(normalized_market),
        )

    def load_eps(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_market = self._validate_market(market)
        normalized_symbol = self._validate_symbol(symbol, normalized_market)
        return self._load_eps_or_empty(
            self._eps_path(normalized_symbol, normalized_market),
            normalized_symbol,
            timezone=self._market_timezone(normalized_market),
        )


class DuckDBMeta:
    """
    Metadata manager backed by DuckDB.

    Default DB path: data/quant.duckdb
    """

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            target: str = str((get_data_dir() / "quant.duckdb").resolve())
        else:
            target = str(db_path)

        if target != ":memory:":
            Path(target).parent.mkdir(parents=True, exist_ok=True)

        self._db_path = target
        self._conn = duckdb.connect(self._db_path)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_meta (
                market      VARCHAR NOT NULL DEFAULT 'tw',
                symbol      VARCHAR NOT NULL,
                freq        VARCHAR NOT NULL,
                source      VARCHAR NOT NULL,
                first_date  TIMESTAMP WITH TIME ZONE,
                last_date   TIMESTAMP WITH TIME ZONE,
                row_count   INTEGER,
                updated_at  TIMESTAMP WITH TIME ZONE,
                PRIMARY KEY (market, symbol, freq)
            );
            """
        )
        if self._has_market_column():
            return

        legacy_rows = self._conn.execute(
            """
            SELECT symbol, freq, source, first_date, last_date, row_count, updated_at
            FROM data_meta;
            """
        ).fetchall()
        self._conn.execute("DROP TABLE data_meta;")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS data_meta (
                market      VARCHAR NOT NULL DEFAULT 'tw',
                symbol      VARCHAR NOT NULL,
                freq        VARCHAR NOT NULL,
                source      VARCHAR NOT NULL,
                first_date  TIMESTAMP WITH TIME ZONE,
                last_date   TIMESTAMP WITH TIME ZONE,
                row_count   INTEGER,
                updated_at  TIMESTAMP WITH TIME ZONE,
                PRIMARY KEY (market, symbol, freq)
            );
            """
        )
        if not legacy_rows:
            return

        self._conn.executemany(
            """
            INSERT INTO data_meta (market, symbol, freq, source, first_date, last_date, row_count, updated_at)
            VALUES ('tw', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (market, symbol, freq) DO UPDATE SET
                source = EXCLUDED.source,
                first_date = EXCLUDED.first_date,
                last_date = EXCLUDED.last_date,
                row_count = EXCLUDED.row_count,
                updated_at = EXCLUDED.updated_at;
            """,
            legacy_rows,
        )

    def _has_market_column(self) -> bool:
        rows = self._conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'data_meta'
            ORDER BY ordinal_position;
            """
        ).fetchall()
        if not rows:
            return False
        columns = {row[0] for row in rows}
        return "market" in columns

    def upsert_meta(
        self,
        symbol: str,
        freq: str,
        source: str,
        first_date: pd.Timestamp,
        last_date: pd.Timestamp,
        row_count: int,
        market: str = "tw",
    ) -> None:
        normalized_market = normalize_market(market)
        self._conn.execute(
            """
            INSERT INTO data_meta (market, symbol, freq, source, first_date, last_date, row_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, NOW())
            ON CONFLICT(market, symbol, freq) DO UPDATE SET
                source = EXCLUDED.source,
                first_date = EXCLUDED.first_date,
                last_date = EXCLUDED.last_date,
                row_count = EXCLUDED.row_count,
                updated_at = NOW();
            """,
            [normalized_market, symbol, freq, source, first_date, last_date, int(row_count)],
        )

    def get_meta(self, symbol: str, freq: str, market: str = "tw") -> dict[str, Any] | None:
        normalized_market = normalize_market(market)
        row = self._conn.execute(
            """
            SELECT market, symbol, freq, source, first_date, last_date, row_count, updated_at
            FROM data_meta
            WHERE market = ? AND symbol = ? AND freq = ?;
            """,
            [normalized_market, symbol, freq],
        ).fetchone()
        if row is None:
            return None

        keys = ["market", "symbol", "freq", "source", "first_date", "last_date", "row_count", "updated_at"]
        return dict(zip(keys, row, strict=True))

    def list_all(self) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT market, symbol, freq, source, first_date, last_date, row_count, updated_at
            FROM data_meta
            ORDER BY market, symbol, freq;
            """
        ).df()

    def close(self) -> None:
        if hasattr(self, "_conn") and self._conn is not None:
            self._conn.close()
            self._conn = None

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:  # noqa: BLE001
            pass
