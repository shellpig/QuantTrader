"""Market friction cost calculators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.market import normalize_market

@dataclass
class TradeCost:
    """Single-trade cost breakdown."""

    commission: float
    tax: float
    slippage: float
    total: float


class TWCostCalculator:
    """Taiwan market commission, tax, and slippage model."""

    def __init__(
        self,
        commission_rate: float = 0.001425,
        commission_discount: float = 0.6,
        tax_rate: float = 0.003,
        etf_tax_rate: float = 0.001,
        slippage_ticks: int = 1,
    ) -> None:
        self.effective_commission_rate = float(commission_rate) * float(commission_discount)
        self.tax_rate = float(tax_rate)
        self.etf_tax_rate = float(etf_tax_rate)
        self.slippage_ticks = int(slippage_ticks)

    def calculate(
        self,
        price: float,
        quantity: int,
        side: str,
        is_etf: bool = False,
    ) -> TradeCost:
        side_normalized = side.upper()
        if side_normalized not in {"BUY", "SELL"}:
            raise ValueError("side must be 'BUY' or 'SELL'.")
        if price <= 0:
            raise ValueError("price must be positive.")
        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        turnover = float(price) * int(quantity)
        commission = max(turnover * self.effective_commission_rate, 20.0)

        if side_normalized == "SELL":
            tax_rate = self.etf_tax_rate if is_etf else self.tax_rate
            tax = turnover * tax_rate
        else:
            tax = 0.0

        slippage = self.get_tick_size(price) * self.slippage_ticks * int(quantity)
        total = commission + tax + slippage

        return TradeCost(
            commission=float(commission),
            tax=float(tax),
            slippage=float(slippage),
            total=float(total),
        )

    @staticmethod
    def get_tick_size(price: float) -> float:
        """Return Taiwan stock tick size based on current price."""
        if price < 10:
            return 0.01
        if price < 50:
            return 0.05
        if price < 100:
            return 0.10
        if price < 500:
            return 0.50
        if price < 1000:
            return 1.00
        return 5.00

    def apply_slippage(self, price: float, side: str) -> float:
        """Return simulated execution price after slippage."""
        side_normalized = side.upper()
        if side_normalized not in {"BUY", "SELL"}:
            raise ValueError("side must be 'BUY' or 'SELL'.")
        tick_size = self.get_tick_size(price)
        adjust = tick_size * self.slippage_ticks
        if side_normalized == "BUY":
            return float(price + adjust)
        return float(price - adjust)


class USCostCalculator:
    """US market cost model for US-1."""

    def __init__(
        self,
        commission_per_trade: float = 0.0,
        slippage_ticks: int = 1,
        tick_size: float = 0.01,
    ) -> None:
        if tick_size <= 0:
            raise ValueError("tick_size must be positive.")
        self.commission_per_trade = float(commission_per_trade)
        self.slippage_ticks = int(slippage_ticks)
        self.tick_size = float(tick_size)

    def calculate(
        self,
        price: float,
        quantity: int,
        side: str,
        is_etf: bool = False,  # noqa: ARG002 - keep API-compatible signature
    ) -> TradeCost:
        side_normalized = side.upper()
        if side_normalized not in {"BUY", "SELL"}:
            raise ValueError("side must be 'BUY' or 'SELL'.")
        if price <= 0:
            raise ValueError("price must be positive.")
        if quantity <= 0:
            raise ValueError("quantity must be positive.")

        commission = self.commission_per_trade
        tax = 0.0
        slippage = self.tick_size * self.slippage_ticks * int(quantity)
        total = commission + tax + slippage
        return TradeCost(
            commission=float(commission),
            tax=float(tax),
            slippage=float(slippage),
            total=float(total),
        )

    def get_tick_size(self, price: float) -> float:  # noqa: ARG002 - stable interface
        return self.tick_size

    def apply_slippage(self, price: float, side: str) -> float:
        side_normalized = side.upper()
        if side_normalized not in {"BUY", "SELL"}:
            raise ValueError("side must be 'BUY' or 'SELL'.")
        adjust = self.tick_size * self.slippage_ticks
        if side_normalized == "BUY":
            return float(price + adjust)
        return float(price - adjust)


def create_cost_calculator(market: str = "tw", **kwargs: Any) -> TWCostCalculator | USCostCalculator:
    normalized_market = normalize_market(market)
    if normalized_market == "tw":
        return TWCostCalculator(**kwargs)
    if normalized_market == "us":
        return USCostCalculator(**kwargs)
    raise ValueError(f"Unknown market: {market}")


# Backward compatibility for modules/tests still importing CostCalculator.
CostCalculator = TWCostCalculator
