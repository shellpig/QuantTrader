"""KD (Stochastic Oscillator) crossover strategy."""

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


class KDCrossStrategy(StrategyBase):
    """
    Stochastic Oscillator (KD) crossover strategy.

    Emits +1 when K crosses above D (golden cross).
    Emits -1 when K crosses below D (death cross).
    """

    def __init__(
        self,
        k_period: int = 9,
        d_period: int = 3,
        smooth_k: int = 3,
    ) -> None:
        if int(k_period) <= 0:
            raise ValueError("k_period must be positive.")
        if int(d_period) <= 0:
            raise ValueError("d_period must be positive.")
        if int(smooth_k) <= 0:
            raise ValueError("smooth_k must be positive.")
        self.k_period = int(k_period)
        self.d_period = int(d_period)
        self.smooth_k = int(smooth_k)
        self._high_history: list[float] = []
        self._low_history: list[float] = []
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return self.k_period + self.smooth_k + self.d_period - 1

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        stoch = pandas_ta.stoch(
            high=pd.to_numeric(df["high"], errors="coerce"),
            low=pd.to_numeric(df["low"], errors="coerce"),
            close=pd.to_numeric(df["close"], errors="coerce"),
            k=self.k_period,
            d=self.d_period,
            smooth_k=self.smooth_k,
        )
        k_cols = [c for c in stoch.columns if c.startswith("STOCHk_")]
        d_cols = [c for c in stoch.columns if c.startswith("STOCHd_")]
        if not k_cols or not d_cols:
            return pd.Series(0, index=df.index, dtype="int8")

        k = stoch[k_cols[0]]
        d = stoch[d_cols[0]]
        prev_k = k.shift(1)
        prev_d = d.shift(1)

        signal = pd.Series(0, index=df.index, dtype="int8")
        valid = k.notna() & d.notna() & prev_k.notna() & prev_d.notna()
        signal.loc[valid & (prev_k <= prev_d) & (k > d)] = 1
        signal.loc[valid & (prev_k >= prev_d) & (k < d)] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        self._high_history.append(float(bar.high))
        self._low_history.append(float(bar.low))
        self._close_history.append(float(bar.close))
        if len(self._close_history) < self.warmup_period + 1:
            return []

        high_s = pd.Series(self._high_history, dtype="float64")
        low_s = pd.Series(self._low_history, dtype="float64")
        close_s = pd.Series(self._close_history, dtype="float64")
        stoch = pandas_ta.stoch(
            high=high_s, low=low_s, close=close_s,
            k=self.k_period, d=self.d_period, smooth_k=self.smooth_k,
        )
        if stoch is None:
            return []
        k_cols = [c for c in stoch.columns if c.startswith("STOCHk_")]
        d_cols = [c for c in stoch.columns if c.startswith("STOCHd_")]
        if not k_cols or not d_cols:
            return []

        curr_k = stoch[k_cols[0]].iloc[-1]
        curr_d = stoch[d_cols[0]].iloc[-1]
        prev_k = stoch[k_cols[0]].iloc[-2]
        prev_d = stoch[d_cols[0]].iloc[-2]
        if pd.isna(curr_k) or pd.isna(curr_d) or pd.isna(prev_k) or pd.isna(prev_d):
            return []

        position_qty = account.get_position(bar.symbol)
        orders: list[OrderEvent] = []
        if prev_k <= prev_d and curr_k > curr_d and position_qty == 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
            )
        elif prev_k >= prev_d and curr_k < curr_d and position_qty > 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="SELL", quantity=position_qty)
            )
        return orders

    def reset_runtime_state(self) -> None:
        self._high_history = []
        self._low_history = []
        self._close_history = []
