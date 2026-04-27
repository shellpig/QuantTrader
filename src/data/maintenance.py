"""Data maintenance workflows for refresh/rebuild/validation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd

from src.data.cleaner import DataCleaner, QualityReport, adjust_prices
from src.data.fetcher import IDataFetcher
from src.data.storage import DuckDBMeta, ParquetStorage


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

    def rebuild_symbol(self, symbol: str) -> QualityReport:
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
        today = datetime.now().strftime("%Y-%m-%d")
        raw_df = self.fetcher.fetch_daily(symbol=symbol, start="2000-01-01", end=today)
        cleaned_df, report = self.cleaner.clean(raw_df, symbol=symbol)
        self.storage.save_daily(symbol, cleaned_df)
        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=cleaned_df)
        self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=cleaned_df)
        return report

    def rebuild_adj_factors(self, symbol: str) -> None:
        """Recompute adjusted prices from stored raw daily data."""
        raw_df = self.storage.load_daily(symbol)
        if raw_df.empty:
            return

        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=raw_df)

    def validate_data(self, symbol: str) -> QualityReport:
        """Run L1/L2 validation against stored raw data."""
        raw_df = self.storage.load_daily(symbol)
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

    def update_daily(self, symbol: str) -> int:
        """
        Incremental daily update from last saved date + 1 day to today.

        Returns number of new rows added.
        """
        existing = self.storage.load_daily(symbol)
        today = datetime.now().strftime("%Y-%m-%d")
        if existing.empty:
            start = "2000-01-01"
        else:
            last_date = pd.to_datetime(existing["date"], errors="coerce").dropna().max()
            if pd.isna(last_date):
                start = "2000-01-01"
            else:
                start = (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")

        new_df = self.fetcher.fetch_daily(symbol=symbol, start=start, end=today)
        if new_df.empty:
            self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=existing)
            self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=existing)
            return 0

        cleaned_new, _ = self.cleaner.clean(new_df, symbol=symbol)
        before_count = len(existing)
        self.storage.save_daily(symbol, cleaned_new)
        merged = self.storage.load_daily(symbol)
        self._rebuild_adjusted_from_raw(symbol=symbol, raw_df=merged)
        self._update_meta(symbol=symbol, freq="daily", source=self._source_name(), df=merged)
        return max(0, len(merged) - before_count)

    def _rebuild_adjusted_from_raw(self, symbol: str, raw_df: pd.DataFrame) -> None:
        if raw_df.empty:
            return

        dividends = self._fetch_dividends(symbol)
        splits = self._fetch_splits(symbol)
        adjusted_df = adjust_prices(raw_df, dividends, splits=splits, method="forward")
        self.storage.save_adjusted(symbol, adjusted_df)
        if not splits.empty:
            self.storage.save_splits(symbol, splits)
            self._update_meta(symbol=symbol, freq="splits", source=self._source_name(), df=splits)

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

    def _update_meta(self, symbol: str, freq: str, source: str, df: pd.DataFrame) -> None:
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
        )
