"""Shared helpers for backtest engines."""

from __future__ import annotations

from collections.abc import Callable

from src.backtest.cost import TWCostCalculator, USCostCalculator, create_cost_calculator
from src.core.config import get_config


ETF_SYMBOLS: frozenset[str] = frozenset({"0050", "0051", "0056", "006208", "00878", "00919"})


def is_etf_symbol(symbol: str, market: str = "tw") -> bool:
    if str(market).strip().lower() != "tw":
        return False
    if symbol in ETF_SYMBOLS:
        return True
    return len(symbol) == 4 and symbol.startswith("00")


def build_cost_calculator_from_config(market: str = "tw") -> TWCostCalculator | USCostCalculator:
    normalized_market = str(market).strip().lower()
    if normalized_market == "us":
        return create_cost_calculator(market="us")

    try:
        cfg = get_config().get("backtest", {})
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}

    return create_cost_calculator(
        market="tw",
        commission_rate=float(cfg.get("commission_rate", 0.001425)),
        commission_discount=float(cfg.get("commission_discount", 0.6)),
        tax_rate=float(cfg.get("tax_rate", 0.003)),
        etf_tax_rate=float(cfg.get("etf_tax_rate", 0.001)),
        slippage_ticks=int(cfg.get("slippage_ticks", 1)),
    )


def calculate_max_buy_quantity(
    *,
    cash: float,
    price: float,
    cost_calculator: TWCostCalculator | USCostCalculator,
    is_etf: bool,
) -> int:
    """
    Return max shares buyable within cash, accounting for buy commission.

    Prefers whole lots (multiples of 1000), falls back to odd lots.
    Uses commission-only affordability check; callers that bake slippage
    into price already get the correct result without double-counting.
    """
    if cash <= 0 or price <= 0:
        return 0
    upper = int(cash // price)
    if upper <= 0:
        return 0

    def _total_spend(qty: int) -> float:
        return float(
            price * qty
            + cost_calculator.calculate(price=price, quantity=qty, side="BUY", is_etf=is_etf).commission
        )

    whole_lot_upper = (upper // 1000) * 1000
    if whole_lot_upper > 0:
        qty = _binary_search_max_affordable(cash, whole_lot_upper, 1000, _total_spend)
        if qty > 0:
            return qty

    return _binary_search_max_affordable(cash, upper, 1, _total_spend)


def _binary_search_max_affordable(
    cash: float,
    upper: int,
    step: int,
    total_spend_fn: Callable[[int], float],
) -> int:
    """Binary search for the largest multiple of step that fits within cash."""
    if upper <= 0 or step <= 0:
        return 0

    units_high = upper // step
    if units_high <= 0:
        return 0

    quantity_upper = units_high * step
    if total_spend_fn(quantity_upper) <= cash:
        return quantity_upper

    units_low = 1
    best_units = 0
    while units_low <= units_high:
        units_mid = (units_low + units_high) // 2
        if total_spend_fn(units_mid * step) <= cash:
            best_units = units_mid
            units_low = units_mid + 1
        else:
            units_high = units_mid - 1

    return best_units * step
