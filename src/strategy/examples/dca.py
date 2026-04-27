"""Dollar-cost-averaging strategy metadata carrier."""

from __future__ import annotations

import pandas as pd

from src.strategy.base import StrategyBase


class DollarCostAveragingStrategy(StrategyBase):
    """
    DCA strategy parameters container.

    The actual execution is handled by DCA-specific backtest flow because
    monthly contribution logic differs from generic signal-driven engines.
    """

    def __init__(
        self,
        *,
        monthly_day: int = 5,
        monthly_amount: float = 10_000.0,
        min_buy_unit: int = 1,
        non_trading_day_policy: str = "next_trading_day",
        buy_price_field: str = "close",
    ) -> None:
        if not 1 <= int(monthly_day) <= 31:
            raise ValueError("monthly_day must be within 1..31.")
        if float(monthly_amount) <= 0:
            raise ValueError("monthly_amount must be positive.")
        if int(min_buy_unit) < 1:
            raise ValueError("min_buy_unit must be >= 1.")
        if str(non_trading_day_policy).strip().lower() != "next_trading_day":
            raise ValueError("Only non_trading_day_policy='next_trading_day' is supported.")
        if str(buy_price_field).strip().lower() != "close":
            raise ValueError("Only buy_price_field='close' is supported.")

        self.monthly_day = int(monthly_day)
        self.monthly_amount = float(monthly_amount)
        self.min_buy_unit = int(min_buy_unit)
        self.non_trading_day_policy = "next_trading_day"
        self.buy_price_field = "close"

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        # DCA does not use generic +1/-1 vector signals.
        return pd.Series(0, index=df.index, dtype="int8")

    def on_bar(self, bar, account) -> list:
        _ = (bar, account)
        # DCA execution is handled by dedicated runner.
        return []
