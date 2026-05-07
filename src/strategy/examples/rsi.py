"""RSI overbought/oversold strategy."""

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


class RSIStrategy(StrategyBase):
    """
    RSI overbought/oversold strategy.

    Emits +1 when RSI recovers above the oversold threshold (exits oversold zone).
    Emits -1 when RSI falls back below the overbought threshold (exits overbought zone).
    """

    def __init__(
        self,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ) -> None:
        if int(period) <= 0:
            raise ValueError("period must be positive.")
        if not (0 <= float(oversold) < float(overbought) <= 100):
            raise ValueError("oversold and overbought must satisfy 0 <= oversold < overbought <= 100.")
        self.period = int(period)
        self.oversold = float(oversold)
        self.overbought = float(overbought)
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return self.period

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = pd.to_numeric(df["close"], errors="coerce")
        rsi = pandas_ta.rsi(close, length=self.period)

        prev_rsi = rsi.shift(1)
        signal = pd.Series(0, index=df.index, dtype="int8")
        valid = rsi.notna() & prev_rsi.notna()
        # Buy: RSI exits oversold zone upward
        signal.loc[valid & (prev_rsi < self.oversold) & (rsi >= self.oversold)] = 1
        # Sell: RSI exits overbought zone downward
        signal.loc[valid & (prev_rsi > self.overbought) & (rsi <= self.overbought)] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        self._close_history.append(float(bar.close))
        if len(self._close_history) < self.warmup_period + 1:
            return []

        close_s = pd.Series(self._close_history, dtype="float64")
        rsi_series = pandas_ta.rsi(close_s, length=self.period)

        curr_rsi = rsi_series.iloc[-1]
        prev_rsi = rsi_series.iloc[-2]
        if pd.isna(curr_rsi) or pd.isna(prev_rsi):
            return []

        position_qty = account.get_position(bar.symbol)
        orders: list[OrderEvent] = []
        if prev_rsi < self.oversold and curr_rsi >= self.oversold and position_qty == 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
            )
        elif prev_rsi > self.overbought and curr_rsi <= self.overbought and position_qty > 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="SELL", quantity=position_qty)
            )
        return orders

    def reset_runtime_state(self) -> None:
        self._close_history = []
