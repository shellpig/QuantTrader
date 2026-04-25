"""Moving-average crossover strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.strategy.base import StrategyBase

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent, OrderEvent


class MACrossStrategy(StrategyBase):
    """
    Double moving-average crossover strategy.

    A golden cross emits +1 and a death cross emits -1.
    Non-cross bars emit 0.
    """

    def __init__(self, ma_short: int = 20, ma_long: int = 60) -> None:
        if ma_short <= 0 or ma_long <= 0:
            raise ValueError("ma_short and ma_long must be positive integers.")
        if ma_short >= ma_long:
            raise ValueError("ma_short must be smaller than ma_long.")
        self.ma_short = int(ma_short)
        self.ma_long = int(ma_long)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if "close" not in df.columns:
            raise ValueError("Input dataframe must include 'close' column.")

        close = pd.to_numeric(df["close"], errors="coerce")
        ma_short_series = close.rolling(self.ma_short, min_periods=self.ma_short).mean()
        ma_long_series = close.rolling(self.ma_long, min_periods=self.ma_long).mean()

        trend = pd.Series(-1, index=df.index, dtype="int8")
        has_ma = ma_short_series.notna() & ma_long_series.notna()
        trend.loc[has_ma & (ma_short_series > ma_long_series)] = 1
        trend.loc[has_ma & (ma_short_series <= ma_long_series)] = -1

        signal = pd.Series(0, index=df.index, dtype="int8")
        trend_change = trend.diff()
        signal.loc[trend_change == 2] = 1
        signal.loc[trend_change == -2] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        _ = (bar, account)
        return []
