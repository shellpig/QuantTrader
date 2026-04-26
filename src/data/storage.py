"""Parquet and DuckDB storage utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb
import pandas as pd

from src.core.config import get_data_dir
from src.core.constants import STANDARD_COLUMNS, TAIPEI_TZ
from src.core.exceptions import StorageError


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


def _normalize_market_df(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
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

    series = out["date"]
    if series.dt.tz is None:
        out["date"] = series.dt.tz_localize(TAIPEI_TZ)
    else:
        out["date"] = series.dt.tz_convert(TAIPEI_TZ)
    out["date"] = out["date"].astype(f"datetime64[ns, {TAIPEI_TZ}]")

    for price_col in ("open", "high", "low", "close"):
        out[price_col] = pd.to_numeric(out[price_col], errors="coerce")
    out = out.dropna(subset=["open", "high", "low", "close"]).copy()
    if out.empty:
        return _empty_standard_dataframe()

    out["open"] = out["open"].astype("float64")
    out["high"] = out["high"].astype("float64")
    out["low"] = out["low"].astype("float64")
    out["close"] = out["close"].astype("float64")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce").fillna(0).astype("int64")

    return out[STANDARD_COLUMNS].sort_values("date").reset_index(drop=True)


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
        normalized = "tw" if market is None else str(market).strip().lower()
        if normalized != "tw":
            raise StorageError(f"Unsupported market: {market}")
        return normalized

    def _validate_symbol(self, symbol: str) -> str:
        if not isinstance(symbol, str):
            raise StorageError("Symbol must be a non-empty string.")

        normalized = str(symbol).strip()
        if not normalized:
            raise StorageError("Symbol must be a non-empty string.")

        if ".." in normalized or "/" in normalized or "\\" in normalized:
            raise StorageError(f"Invalid symbol path segment: {symbol}")

        symbol_path = Path(normalized)
        if symbol_path.is_absolute() or symbol_path.anchor:
            raise StorageError(f"Invalid symbol path segment: {symbol}")

        return normalized

    def _build_market_path(self, layer: str, market: str, symbol: str, filename: str) -> Path:
        path = (self.data_dir / layer / market / symbol / filename).resolve(strict=False)
        try:
            path.relative_to(self.data_dir)
        except ValueError as exc:
            raise StorageError(f"Resolved path escapes data_dir: {path}") from exc
        return path

    def _daily_path(self, symbol: str, market: str = "tw") -> Path:
        return self._build_market_path(
            "raw",
            self._validate_market(market),
            self._validate_symbol(symbol),
            "daily.parquet",
        )

    def _minute_path(self, symbol: str, market: str = "tw") -> Path:
        return self._build_market_path(
            "raw",
            self._validate_market(market),
            self._validate_symbol(symbol),
            "minute.parquet",
        )

    def _adjusted_path(self, symbol: str, market: str = "tw") -> Path:
        return self._build_market_path(
            "processed",
            self._validate_market(market),
            self._validate_symbol(symbol),
            "adj_daily.parquet",
        )

    def _save_with_upsert(self, path: Path, symbol: str, df: pd.DataFrame) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        incoming = _normalize_market_df(df, symbol)

        if path.exists():
            existing = self._load_or_empty(path, symbol)
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

    def _load_or_empty(self, path: Path, symbol: str) -> pd.DataFrame:
        if not path.exists():
            return _empty_standard_dataframe()
        try:
            loaded = pd.read_parquet(path)
        except Exception as exc:  # noqa: BLE001
            raise StorageError(f"Failed to read parquet: {path}") from exc
        return _normalize_market_df(loaded, symbol=symbol)

    def save_daily(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_symbol = self._validate_symbol(symbol)
        return self._save_with_upsert(self._daily_path(normalized_symbol, market), normalized_symbol, df)

    def load_daily(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_symbol = self._validate_symbol(symbol)
        return self._load_or_empty(self._daily_path(normalized_symbol, market), normalized_symbol)

    def save_minute(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_symbol = self._validate_symbol(symbol)
        return self._save_with_upsert(self._minute_path(normalized_symbol, market), normalized_symbol, df)

    def load_minute(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_symbol = self._validate_symbol(symbol)
        return self._load_or_empty(self._minute_path(normalized_symbol, market), normalized_symbol)

    def save_adjusted(self, symbol: str, df: pd.DataFrame, market: str = "tw") -> Path:
        normalized_symbol = self._validate_symbol(symbol)
        return self._save_with_upsert(self._adjusted_path(normalized_symbol, market), normalized_symbol, df)

    def load_adjusted(self, symbol: str, market: str = "tw") -> pd.DataFrame:
        normalized_symbol = self._validate_symbol(symbol)
        return self._load_or_empty(self._adjusted_path(normalized_symbol, market), normalized_symbol)


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
                symbol      VARCHAR NOT NULL,
                freq        VARCHAR NOT NULL,
                source      VARCHAR NOT NULL,
                first_date  TIMESTAMP WITH TIME ZONE,
                last_date   TIMESTAMP WITH TIME ZONE,
                row_count   INTEGER,
                updated_at  TIMESTAMP WITH TIME ZONE,
                PRIMARY KEY (symbol, freq)
            );
            """
        )

    def upsert_meta(
        self,
        symbol: str,
        freq: str,
        source: str,
        first_date: pd.Timestamp,
        last_date: pd.Timestamp,
        row_count: int,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO data_meta (symbol, freq, source, first_date, last_date, row_count, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NOW())
            ON CONFLICT(symbol, freq) DO UPDATE SET
                source = EXCLUDED.source,
                first_date = EXCLUDED.first_date,
                last_date = EXCLUDED.last_date,
                row_count = EXCLUDED.row_count,
                updated_at = NOW();
            """,
            [symbol, freq, source, first_date, last_date, int(row_count)],
        )

    def get_meta(self, symbol: str, freq: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT symbol, freq, source, first_date, last_date, row_count, updated_at
            FROM data_meta
            WHERE symbol = ? AND freq = ?;
            """,
            [symbol, freq],
        ).fetchone()
        if row is None:
            return None

        keys = ["symbol", "freq", "source", "first_date", "last_date", "row_count", "updated_at"]
        return dict(zip(keys, row, strict=True))

    def list_all(self) -> pd.DataFrame:
        return self._conn.execute(
            """
            SELECT symbol, freq, source, first_date, last_date, row_count, updated_at
            FROM data_meta
            ORDER BY symbol, freq;
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
