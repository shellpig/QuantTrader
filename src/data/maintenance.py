"""Data maintenance workflows for refresh/rebuild/validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time

import pandas as pd

from src.core.market import normalize_market
from src.data.cleaner import DataCleaner, QualityReport, adjust_prices
from src.data.fetcher import IDataFetcher
from src.data.storage import DuckDBMeta, ParquetStorage

US_YFINANCE_REQUEST_INTERVAL_SECONDS = 1.0


def _empty_dividends() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype="datetime64[ns]"),
            "cash_dividend": pd.Series(dtype="float64"),
            "stock_dividend": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )


def _empty_splits() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.Series(dtype="datetime64[ns]"),
            "before_price": pd.Series(dtype="float64"),
            "after_price": pd.Series(dtype="float64"),
            "symbol": pd.Series(dtype="object"),
        }
    )


class DataMaintenance:
    """
    Data maintenance operations.

    Dependencies are injected for testability.
    """

    def __init__(
        self,
        fetcher: IDataFetcher,
        storage: ParquetStorage,
        meta: DuckDBMeta,
        cleaner: DataCleaner,
    ):
        self.fetcher = fetcher
        self.storage = storage
        self.meta = meta
        self.cleaner = cleaner
        self._last_us_yfinance_request_ts: float | None = None

    def rebuild_symbol(self, symbol: str, market: str = "tw") -> QualityReport:
        """
        Fully rebuild one symbol:
        1. Download full daily history
        2. Download dividends
        3. Run L1/L2 cleaning
        4. Compute forward-adjusted prices
        5. Save raw + processed
        6. Update metadata
        7. Return quality report
        """
        normalized_market = normalize_market(market)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self._supports_us_adjusted_bundle(normalized_market):
            raw_df, adjusted_df, splits_df, _ = self._fetch_us_daily_bundle(symbol=symbol, start="2000-01-01", end=today)
            cleaned_df, report = self.cleaner.clean(raw_df, symbol=symbol)
            self.storage.save_daily(symbol, cleaned_df, market=normalized_market)
            self.storage.save_adjusted(
                symbol,
                self._filter_adjusted_by_cleaned_dates(adjusted_df=adjusted_df, cleaned_df=cleaned_df),
                market=normalized_market,
            )
            if not splits_df.empty:
                self.storage.save_splits(symbol, splits_df, market=normalized_market)
                self._update_meta(symbol=symbol, freq="splits", source=self._source_name(), df=splits_df, market=normalized_market)
            self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=cleaned_df, market=normalized_market)
            return report

        raw_df = self.fetcher.fetch_daily(symbol=symbol, start="2000-01-01", end=today)
        cleaned_df, report = self.cleaner.clean(raw_df, symbol=symbol)
        self.storage.save_daily(symbol, cleaned_df, market=normalized_market)
        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=cleaned_df, market=normalized_market)
        self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=cleaned_df, market=normalized_market)
        return report

    def rebuild_adj_factors(self, symbol: str, market: str = "tw") -> None:
        """Recompute adjusted prices from stored raw daily data."""
        normalized_market = normalize_market(market)
        if self._supports_us_adjusted_bundle(normalized_market):
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            raw_df, adjusted_df, splits_df, _ = self._fetch_us_daily_bundle(symbol=symbol, start="2000-01-01", end=today)
            cleaned_df, _ = self.cleaner.clean(raw_df, symbol=symbol)
            self.storage.save_adjusted(
                symbol,
                self._filter_adjusted_by_cleaned_dates(adjusted_df=adjusted_df, cleaned_df=cleaned_df),
                market=normalized_market,
            )
            if not splits_df.empty:
                self.storage.save_splits(symbol, splits_df, market=normalized_market)
                self._update_meta(symbol=symbol, freq="splits", source=self._source_name(), df=splits_df, market=normalized_market)
            return

        raw_df = self.storage.load_daily(symbol, market=normalized_market)
        if raw_df.empty:
            return

        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=raw_df, market=normalized_market)

    def validate_data(self, symbol: str, market: str = "tw") -> QualityReport:
        """Run L1/L2 validation against stored raw data."""
        normalized_market = normalize_market(market)
        raw_df = self.storage.load_daily(symbol, market=normalized_market)
        _, report = self.cleaner.clean(raw_df, symbol=symbol)
        return report

    def list_stale_symbols(self, days: int = 7) -> list[dict]:
        """List metadata rows whose updated_at is older than N days."""
        rows = self.meta.list_all()
        if rows.empty:
            return []

        threshold = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=days))
        updated_series = pd.to_datetime(rows["updated_at"], errors="coerce", utc=True)
        stale_mask = updated_series < threshold
        stale = rows.loc[stale_mask].copy()
        if stale.empty:
            return []
        return stale.to_dict(orient="records")

    def update_daily(self, symbol: str, market: str = "tw") -> int:
        """
        Incremental daily update from last saved date + 1 day to today.

        Returns number of new rows added.
        """
        normalized_market = normalize_market(market)
        existing = self.storage.load_daily(symbol, market=normalized_market)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if existing.empty:
            start = "2000-01-01"
        else:
            last_date = pd.to_datetime(existing["date"], errors="coerce").dropna().max()
            if pd.isna(last_date):
                start = "2000-01-01"
            else:
                start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        if self._supports_us_adjusted_bundle(normalized_market):
            raw_new, adjusted_new, splits_df, _ = self._fetch_us_daily_bundle(symbol=symbol, start=start, end=today)
            if raw_new.empty:
                self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=existing, market=normalized_market)
                return 0

            cleaned_new, _ = self.cleaner.clean(raw_new, symbol=symbol)
            before_count = len(existing)
            self.storage.save_daily(symbol, cleaned_new, market=normalized_market)
            self.storage.save_adjusted(
                symbol,
                self._filter_adjusted_by_cleaned_dates(adjusted_df=adjusted_new, cleaned_df=cleaned_new),
                market=normalized_market,
            )
            if not splits_df.empty:
                self.storage.save_splits(symbol, splits_df, market=normalized_market)
                self._update_meta(symbol=symbol, freq="splits", source=self._source_name(), df=splits_df, market=normalized_market)
            merged = self.storage.load_daily(symbol, market=normalized_market)
            self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=merged, market=normalized_market)
            return max(0, len(merged) - before_count)

        new_df = self.fetcher.fetch_daily(symbol=symbol, start=start, end=today)
        if new_df.empty:
            self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=existing, market=normalized_market)
            self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=existing, market=normalized_market)
            return 0

        cleaned_new, _ = self.cleaner.clean(new_df, symbol=symbol)
        before_count = len(existing)
        self.storage.save_daily(symbol, cleaned_new, market=normalized_market)
        merged = self.storage.load_daily(symbol, market=normalized_market)
        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=merged, market=normalized_market)
        self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=merged, market=normalized_market)
        return max(0, len(merged) - before_count)

    def _rebuild_adjusted_from_raw(self, symbol: str, raw_df: pd.DataFrame, market: str) -> None:
        if raw_df.empty:
            return

        dividends = self._fetch_dividends(symbol)
        splits = self._fetch_splits(symbol)
        adjusted_df = adjust_prices(raw_df, dividends, splits=splits, method="forward")
        self.storage.save_adjusted(symbol, adjusted_df, market=market)
        if not splits.empty:
            self.storage.save_splits(symbol, splits, market=market)
            self._update_meta(symbol=symbol, freq="splits", source=self._source_name(), df=splits, market=market)

    def _fetch_dividends(self, symbol: str) -> pd.DataFrame:
        method = getattr(self.fetcher, "fetch_dividends", None)
        if callable(method):
            return method(symbol=symbol)
        return _empty_dividends()

    def _fetch_splits(self, symbol: str) -> pd.DataFrame:
        method = getattr(self.fetcher, "fetch_splits", None)
        if callable(method):
            return method(symbol=symbol)
        return _empty_splits()

    def _source_name(self) -> str:
        cls = self.fetcher.__class__.__name__.lower()
        return cls.replace("fetcher", "")

    def _update_meta(self, symbol: str, freq: str, source: str, df: pd.DataFrame, market: str = "tw") -> None:
        if df.empty:
            return

        dates = pd.to_datetime(df["date"], errors="coerce").dropna()
        if dates.empty:
            return

        self.meta.upsert_meta(
            symbol=symbol,
            freq=freq,
            source=source,
            first_date=dates.min(),
            last_date=dates.max(),
            row_count=len(df),
            market=market,
        )

    def _supports_us_adjusted_bundle(self, market: str) -> bool:
        if market != "us":
            return False
        if self._source_name() != "yfinance":
            return False
        return callable(getattr(self.fetcher, "fetch_daily_with_adjusted", None))

    def _maybe_throttle_us_yfinance(self) -> None:
        if self._last_us_yfinance_request_ts is None:
            return
        elapsed = time.monotonic() - self._last_us_yfinance_request_ts
        if elapsed >= US_YFINANCE_REQUEST_INTERVAL_SECONDS:
            return
        time.sleep(US_YFINANCE_REQUEST_INTERVAL_SECONDS - elapsed)

    def _fetch_us_daily_bundle(self, symbol: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, bool]:
        self._maybe_throttle_us_yfinance()
        method = getattr(self.fetcher, "fetch_daily_with_adjusted", None)
        if not callable(method):
            raise RuntimeError("US adjusted bundle is not available from current fetcher.")
        try:
            raw_df, adjusted_df, splits_df, volume_adjusted = method(symbol=symbol, start=start, end=end)
        finally:
            self._last_us_yfinance_request_ts = time.monotonic()
        return raw_df, adjusted_df, splits_df, bool(volume_adjusted)

    def _filter_adjusted_by_cleaned_dates(self, adjusted_df: pd.DataFrame, cleaned_df: pd.DataFrame) -> pd.DataFrame:
        if adjusted_df.empty or cleaned_df.empty:
            return adjusted_df.iloc[0:0].copy()
        clean_dates = pd.to_datetime(cleaned_df["date"], errors="coerce").dropna()
        adjusted_dates = pd.to_datetime(adjusted_df["date"], errors="coerce")
        out = adjusted_df.loc[adjusted_dates.isin(clean_dates)].copy()
        return out.sort_values("date").reset_index(drop=True)
