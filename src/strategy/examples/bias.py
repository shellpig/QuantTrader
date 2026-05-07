"""Bias (price deviation from moving average) strategy."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from src.backtest.events import OrderEvent
from src.strategy.base import StrategyBase

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent

_BUY_INTENT_QUANTITY = 10**9


class BiasStrategy(StrategyBase):
    """
    Bias (乖離率) mean-reversion strategy.

    BIAS = (close - MA) / MA * 100

    Emits +1 when BIAS crosses below buy_bias (enters oversold zone).
    Emits -1 when BIAS crosses above sell_bias (enters overbought zone).
    """

    def __init__(
        self,
        ma_period: int = 20,
        buy_bias: float = -10.0,
        sell_bias: float = 10.0,
    ) -> None:
        if int(ma_period) <= 0:
            raise ValueError("ma_period must be positive.")
        if float(buy_bias) >= float(sell_bias):
            raise ValueError("buy_bias must be less than sell_bias.")
        self.ma_period = int(ma_period)
        self.buy_bias = float(buy_bias)
        self.sell_bias = float(sell_bias)
        self._close_history: list[float] = []

    @property
    def warmup_period(self) -> int:
        return self.ma_period

    def _compute_bias(self, close: pd.Series) -> pd.Series:
        ma = close.rolling(self.ma_period, min_periods=self.ma_period).mean()
        return (close - ma) / ma * 100

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        close = pd.to_numeric(df["close"], errors="coerce")
        bias = self._compute_bias(close)
        prev_bias = bias.shift(1)

        signal = pd.Series(0, index=df.index, dtype="int8")
        valid = bias.notna() & prev_bias.notna()
        # Buy: BIAS crosses below buy_bias (enters oversold zone)
        signal.loc[valid & (prev_bias >= self.buy_bias) & (bias < self.buy_bias)] = 1
        # Sell: BIAS crosses above sell_bias (enters overbought zone)
        signal.loc[valid & (prev_bias <= self.sell_bias) & (bias > self.sell_bias)] = -1
        return signal

    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        self._close_history.append(float(bar.close))
        if len(self._close_history) < self.warmup_period + 1:
            return []

        close_s = pd.Series(self._close_history, dtype="float64")
        bias_s = self._compute_bias(close_s)

        curr_bias = bias_s.iloc[-1]
        prev_bias = bias_s.iloc[-2]
        if pd.isna(curr_bias) or pd.isna(prev_bias):
            return []

        position_qty = account.get_position(bar.symbol)
        orders: list[OrderEvent] = []
        if prev_bias >= self.buy_bias and curr_bias < self.buy_bias and position_qty == 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="BUY", quantity=_BUY_INTENT_QUANTITY)
            )
        elif prev_bias <= self.sell_bias and curr_bias > self.sell_bias and position_qty > 0:
            orders.append(
                OrderEvent(symbol=bar.symbol, order_type="MARKET", side="SELL", quantity=position_qty)
            )
        return orders

    def reset_runtime_state(self) -> None:
        self._close_history = []
