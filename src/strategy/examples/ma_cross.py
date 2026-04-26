"""Moving-average crossover strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.backtest.events import OrderEvent
from src.strategy.base import StrategyBase

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent

_BUY_INTENT_QUANTITY = 10**9


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
        self._close_history: list[float] = []
        self._prev_trend: int | None = None

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
        self._close_history.append(float(bar.close))

        if len(self._close_history) < self.ma_long:
            return []

        short_window = self._close_history[-self.ma_short :]
        long_window = self._close_history[-self.ma_long :]
        ma_short = sum(short_window) / self.ma_short
        ma_long = sum(long_window) / self.ma_long
        current_trend = 1 if ma_short > ma_long else -1

        # First valid MA bar only initializes trend to avoid warm-up pseudo signal.
        if self._prev_trend is None:
            self._prev_trend = current_trend
            return []

        orders: list[OrderEvent] = []
        position_qty = account.get_position(bar.symbol)

        if self._prev_trend == -1 and current_trend == 1 and position_qty == 0:
            orders.append(
                OrderEvent(
                    symbol=bar.symbol,
                    order_type="MARKET",
                    side="BUY",
                    quantity=_BUY_INTENT_QUANTITY,
                )
            )
        elif self._prev_trend == 1 and current_trend == -1 and position_qty > 0:
            orders.append(
                OrderEvent(
                    symbol=bar.symbol,
                    order_type="MARKET",
                    side="SELL",
                    quantity=position_qty,
                )
            )

        self._prev_trend = current_trend
        return orders

    def reset_runtime_state(self) -> None:
        self._close_history = []
        self._prev_trend = None
