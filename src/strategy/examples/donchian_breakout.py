"""Donchian Channel breakout strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.backtest.events import OrderEvent
from src.strategy.base import StrategyBase

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent

_BUY_INTENT_QUANTITY = 10**9


class DonchianBreakoutStrategy(StrategyBase):
    """
    Donchian Channel breakout strategy.

    Emits +1 when close breaks above the previous entry_period-day high.
    Emits -1 when close breaks below the previous exit_period-day low.

    Both upper and lower channels exclude the current bar (shift(1)).
    """

    def __init__(
        self,
        entry_period: int = 20,
        exit_period: int = 10,
    ) -> None:
        if int(entry_period) <= 0:
            raise ValueError("entry_period must be positive.")
        if int(exit_period) <= 0:
            raise ValueError("exit_period must be positive.")
        self.entry_period = int(entry_period)
        self.exit_period = int(exit_period)
        self._high_history: list[float] = []
        self._low_history: list[float] = []
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return max(self.entry_period, self.exit_period)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        close = pd.to_numeric(df["close"], errors="coerce")

        # Exclude current bar: shift(1) after rolling
        upper = high.rolling(self.entry_period, min_periods=self.entry_period).max().shift(1)
        lower = low.rolling(self.exit_period, min_periods=self.exit_period).min().shift(1)

        signal = pd.Series(0, index=df.index, dtype="int8")
        valid_buy = close.notna() & upper.notna()
        valid_sell = close.notna() & lower.notna()
        signal.loc[valid_buy & (close > upper)] = 1
        signal.loc[valid_sell & (close < lower)] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        # Compute thresholds from PREVIOUS bars before appending current
        orders: list[OrderEvent] = []

        n = len(self._high_history)
        if n >= self.entry_period:
            upper = max(self._high_history[-self.entry_period:])
            if float(bar.close) > upper and account.get_position(bar.symbol) == 0:
                orders.append(
                    OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
                )

        if n >= self.exit_period:
            lower = min(self._low_history[-self.exit_period:])
            if float(bar.close) < lower and account.get_position(bar.symbol) > 0:
                orders.append(
                    OrderEvent(
                        symbol=bar.symbol,
                        order_type="MARKET",
                        side="SELL",
                        quantity=account.get_position(bar.symbol),
                    )
                )

        self._high_history.append(float(bar.high))
        self._low_history.append(float(bar.low))
        self._close_history.append(float(bar.close))
        return orders

    def reset_runtime_state(self) -> None:
        self._high_history = []
        self._low_history = []
        self._close_history = []
