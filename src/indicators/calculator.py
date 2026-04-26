"""Indicator engine built on top of pandas-ta."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd
import pandas_ta as ta

# Taiwan-market naming aliases -> pandas-ta function mapping.
INDICATOR_ALIAS: dict[str, dict[str, Any]] = {
    "KD": {"func": "stoch", "kwargs": {"k": 9, "d": 3, "smooth_k": 3}},
    "RSI_14": {"func": "rsi", "kwargs": {"length": 14}},
    "MACD": {"func": "macd", "kwargs": {"fast": 12, "slow": 26, "signal": 9}},
    "BBANDS_20": {"func": "bbands", "kwargs": {"length": 20, "std": 2.0}},
    "ATR_14": {"func": "atr", "kwargs": {"length": 14}},
    "OBV": {"func": "obv", "kwargs": {}},
    "WILLR": {"func": "willr", "kwargs": {"length": 14}},
    "EMA_12": {"func": "ema", "kwargs": {"length": 12}},
    "EMA_26": {"func": "ema", "kwargs": {"length": 26}},
}


class IndicatorEngine:
    """Technical indicator calculator with normalized output names."""

    _RE_MA = re.compile(r"^(M|EM)A_(\d+)$", flags=re.IGNORECASE)

    def calculate(self, df: pd.DataFrame, indicator_name: str) -> pd.DataFrame:
        """Calculate a single indicator and return standardized columns."""
        if not isinstance(df, pd.DataFrame) or df.empty:
            raise ValueError("Input dataframe must be a non-empty DataFrame.")

        name = str(indicator_name).strip().upper()
        close = self._numeric_series(df, "close")

        dynamic = self._parse_ma(name)
        if dynamic is not None:
            func, length = dynamic
            if func == "sma":
                values = ta.sma(close, length=length)
            else:
                values = ta.ema(close, length=length)
            if values is None:
                raise ValueError(f"Failed to compute indicator: {name}")
            return pd.DataFrame({name: values}, index=df.index)

        spec = INDICATOR_ALIAS.get(name)
        if spec is None:
            raise ValueError(f"Unsupported indicator: {indicator_name}")

        func = str(spec["func"])
        kwargs = dict(spec.get("kwargs", {}))

        if func == "rsi":
            values = ta.rsi(close, **kwargs)
            return pd.DataFrame({name: values}, index=df.index)

        if func == "macd":
            raw = ta.macd(close, **kwargs)
            if raw is None or raw.empty:
                raise ValueError(f"Failed to compute indicator: {name}")
            macd_col = self._find_prefixed_col(raw.columns, "MACD_")
            signal_col = self._find_prefixed_col(raw.columns, "MACDS_")
            hist_col = self._find_prefixed_col(raw.columns, "MACDH_")
            return pd.DataFrame(
                {
                    "macd": raw[macd_col],
                    "signal": raw[signal_col],
                    "histogram": raw[hist_col],
                },
                index=df.index,
            )

        if func == "stoch":
            high = self._numeric_series(df, "high")
            low = self._numeric_series(df, "low")
            raw = ta.stoch(high, low, close, **kwargs)
            if raw is None or raw.empty:
                raise ValueError(f"Failed to compute indicator: {name}")
            k_col = self._find_prefixed_col(raw.columns, "STOCHK_")
            d_col = self._find_prefixed_col(raw.columns, "STOCHD_")
            return pd.DataFrame({"K": raw[k_col], "D": raw[d_col]}, index=df.index)

        if func == "bbands":
            raw = ta.bbands(close, **kwargs)
            if raw is None or raw.empty:
                raise ValueError(f"Failed to compute indicator: {name}")
            upper_col = self._find_prefixed_col(raw.columns, "BBU_")
            middle_col = self._find_prefixed_col(raw.columns, "BBM_")
            lower_col = self._find_prefixed_col(raw.columns, "BBL_")
            return pd.DataFrame(
                {
                    "upper": raw[upper_col],
                    "middle": raw[middle_col],
                    "lower": raw[lower_col],
                },
                index=df.index,
            )

        if func == "atr":
            high = self._numeric_series(df, "high")
            low = self._numeric_series(df, "low")
            values = ta.atr(high, low, close, **kwargs)
            return pd.DataFrame({name: values}, index=df.index)

        if func == "obv":
            volume = self._numeric_series(df, "volume")
            values = ta.obv(close, volume, **kwargs)
            return pd.DataFrame({name: values}, index=df.index)

        if func == "willr":
            high = self._numeric_series(df, "high")
            low = self._numeric_series(df, "low")
            values = ta.willr(high, low, close, **kwargs)
            return pd.DataFrame({name: values}, index=df.index)

        if func == "ema":
            values = ta.ema(close, **kwargs)
            return pd.DataFrame({name: values}, index=df.index)

        raise ValueError(f"Unsupported indicator function mapping: {func}")

    def calculate_batch(self, df: pd.DataFrame, indicator_names: list[str]) -> pd.DataFrame:
        """Calculate multiple indicators and merge by index."""
        if not isinstance(indicator_names, list) or not indicator_names:
            raise ValueError("indicator_names must be a non-empty list.")

        parts = [self.calculate(df, name) for name in indicator_names]
        return pd.concat(parts, axis=1)

    def list_supported(self) -> list[str]:
        """List all supported names including common dynamic MA aliases."""
        supported = set(INDICATOR_ALIAS.keys())
        supported.update({"MA_5", "MA_20", "MA_60"})
        return sorted(supported)

    def _parse_ma(self, name: str) -> tuple[str, int] | None:
        """
        Parse MA_{n} / EMA_{n} dynamic format.

        Examples:
        - MA_5 -> ("sma", 5)
        - EMA_12 -> ("ema", 12)
        """
        match = self._RE_MA.fullmatch(str(name).strip())
        if match is None:
            return None

        prefix = match.group(1).upper()
        length = int(match.group(2))
        if length <= 0:
            return None
        return ("ema" if prefix == "EM" else "sma", length)

    @staticmethod
    def _numeric_series(df: pd.DataFrame, column: str) -> pd.Series:
        if column not in df.columns:
            raise ValueError(f"Input dataframe must include '{column}' column.")
        return pd.to_numeric(df[column], errors="coerce")

    @staticmethod
    def _find_prefixed_col(columns: pd.Index, prefix: str) -> str:
        upper_prefix = prefix.upper()
        for col in columns:
            if str(col).upper().startswith(upper_prefix):
                return str(col)
        raise ValueError(f"Cannot find column with prefix: {prefix}")

