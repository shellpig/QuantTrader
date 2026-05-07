"""Bollinger Band breakout strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd
import pandas_ta

from src.backtest.events import OrderEvent
from src.strategy.base import StrategyBase

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent

_BUY_INTENT_QUANTITY = 10**9


class BollingerBandStrategy(StrategyBase):
    """
    Bollinger Band mean-reversion strategy.

    Emits +1 when close crosses below the lower band (oversold breakout).
    Emits -1 when close crosses above the upper band (overbought breakout).
    """

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> None:
        if int(period) <= 0:
            raise ValueError("period must be positive.")
        if float(std_dev) <= 0:
            raise ValueError("std_dev must be positive.")
        self.period = int(period)
        self.std_dev = float(std_dev)
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return self.period

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = pd.to_numeric(df["close"], errors="coerce")
        bb = pandas_ta.bbands(close, length=self.period, std=self.std_dev)

        lower_cols = [c for c in bb.columns if c.startswith("BBL_")]
        upper_cols = [c for c in bb.columns if c.startswith("BBU_")]
        if not lower_cols or not upper_cols:
            return pd.Series(0, index=df.index, dtype="int8")

        lower = bb[lower_cols[0]]
        upper = bb[upper_cols[0]]
        prev_close = close.shift(1)
        prev_lower = lower.shift(1)
        prev_upper = upper.shift(1)

        signal = pd.Series(0, index=df.index, dtype="int8")
        valid = (
            close.notna() & lower.notna() & upper.notna()
            & prev_close.notna() & prev_lower.notna() & prev_upper.notna()
        )
        # Buy: close crosses below lower band
        signal.loc[valid & (prev_close >= prev_lower) & (close < lower)] = 1
        # Sell: close crosses above upper band
        signal.loc[valid & (prev_close <= prev_upper) & (close > upper)] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        self._close_history.append(float(bar.close))
        if len(self._close_history) < self.warmup_period + 1:
            return []

        close_s = pd.Series(self._close_history, dtype="float64")
        bb = pandas_ta.bbands(close_s, length=self.period, std=self.std_dev)

        lower_cols = [c for c in bb.columns if c.startswith("BBL_")]
        upper_cols = [c for c in bb.columns if c.startswith("BBU_")]
        if not lower_cols or not upper_cols:
            return []

        curr_lower = bb[lower_cols[0]].iloc[-1]
        curr_upper = bb[upper_cols[0]].iloc[-1]
        prev_lower = bb[lower_cols[0]].iloc[-2]
        prev_upper = bb[upper_cols[0]].iloc[-2]
        curr_close = self._close_history[-1]
        prev_close = self._close_history[-2]

        if pd.isna(curr_lower) or pd.isna(curr_upper) or pd.isna(prev_lower) or pd.isna(prev_upper):
            return []

        position_qty = account.get_position(bar.symbol)
        orders: list[OrderEvent] = []
        if prev_close >= prev_lower and curr_close < curr_lower and position_qty == 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
            )
        elif prev_close <= prev_upper and curr_close > curr_upper and position_qty > 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="SELL", quantity=position_qty)
            )
        return orders

    def reset_runtime_state(self) -> None:
        self._close_history = []
