"""Abstract strategy interface for vectorized and event-driven engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import pandas as pd

if TYPE_CHECKING:
    from src.backtest.account import Account
    from src.backtest.events import BarEvent, OrderEvent
else:
    Account = Any
    BarEvent = Any
    OrderEvent = Any


class StrategyBase(ABC):
    """
    Base class for trading strategies.

    - Vectorized engine calls `generate_signals`.
    - Event-driven engine calls `on_bar`.
    """

    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate vectorized signals aligned with `df.index`.

        Signal values:
        - +1: buy
        - -1: sell
        -  0: no action
        """

    @abstractmethod
    def on_bar(self, bar: BarEvent, account: Account) -> list[OrderEvent]:
        """Handle one bar in event-driven mode."""

    def on_fill(self, fill: Any, account: Account) -> None:
        """Callback after an order fill; subclasses may override."""
        _ = (fill, account)
        return None
