"""MACD crossover strategy."""

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


class MACDCrossStrategy(StrategyBase):
    """
    MACD crossover strategy.

    Emits +1 when MACD line crosses above Signal line.
    Emits -1 when MACD line crosses below Signal line.
    """

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> None:
        if int(fast) <= 0:
            raise ValueError("fast must be positive.")
        if int(slow) <= 0:
            raise ValueError("slow must be positive.")
        if int(signal) <= 0:
            raise ValueError("signal must be positive.")
        if int(fast) >= int(slow):
            raise ValueError("fast must be less than slow.")
        self.fast = int(fast)
        self.slow = int(slow)
        self.signal = int(signal)
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return self.slow + self.signal - 1

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = pd.to_numeric(df["close"], errors="coerce")
        macd_df = pandas_ta.macd(close, fast=self.fast, slow=self.slow, signal=self.signal)

        macd_cols = [c for c in macd_df.columns if c.startswith("MACD_")]
        sig_cols = [c for c in macd_df.columns if c.startswith("MACDs_")]
        if not macd_cols or not sig_cols:
            return pd.Series(0, index=df.index, dtype="int8")

        macd_line = macd_df[macd_cols[0]]
        sig_line = macd_df[sig_cols[0]]
        prev_macd = macd_line.shift(1)
        prev_sig = sig_line.shift(1)

        signal_series = pd.Series(0, index=df.index, dtype="int8")
        valid = macd_line.notna() & sig_line.notna() & prev_macd.notna() & prev_sig.notna()
        signal_series.loc[valid & (prev_macd <= prev_sig) & (macd_line > sig_line)] = 1
        signal_series.loc[valid & (prev_macd >= prev_sig) & (macd_line < sig_line)] = -1
        return signal_series

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        self._close_history.append(float(bar.close))
        if len(self._close_history) < self.warmup_period + 1:
            return []

        close_s = pd.Series(self._close_history, dtype="float64")
        macd_df = pandas_ta.macd(close_s, fast=self.fast, slow=self.slow, signal=self.signal)

        macd_cols = [c for c in macd_df.columns if c.startswith("MACD_")]
        sig_cols = [c for c in macd_df.columns if c.startswith("MACDs_")]
        if not macd_cols or not sig_cols:
            return []

        curr_macd = macd_df[macd_cols[0]].iloc[-1]
        curr_sig = macd_df[sig_cols[0]].iloc[-1]
        prev_macd = macd_df[macd_cols[0]].iloc[-2]
        prev_sig = macd_df[sig_cols[0]].iloc[-2]
        if pd.isna(curr_macd) or pd.isna(curr_sig) or pd.isna(prev_macd) or pd.isna(prev_sig):
            return []

        position_qty = account.get_position(bar.symbol)
        orders: list[OrderEvent] = []
        if prev_macd <= prev_sig and curr_macd > curr_sig and position_qty == 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
            )
        elif prev_macd >= prev_sig and curr_macd < curr_sig and position_qty > 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="SELL", quantity=position_qty)
            )
        return orders

    def reset_runtime_state(self) -> None:
        self._close_history = []
