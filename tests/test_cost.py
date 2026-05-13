from __future__ import annotations

import pytest

from src.backtest.cost import (
    CostCalculator,
    TWCostCalculator,
    USCostCalculator,
    create_cost_calculator,
)


def test_create_cost_calculator_returns_tw_by_default() -> None:
    calc = create_cost_calculator()
    assert isinstance(calc, TWCostCalculator)


def test_create_cost_calculator_returns_us() -> None:
    calc = create_cost_calculator(market="us")
    assert isinstance(calc, USCostCalculator)


def test_create_cost_calculator_rejects_unknown_market() -> None:
    with pytest.raises(ValueError):
        create_cost_calculator(market="hk")


def test_us_cost_calculator_defaults_to_zero_tax_and_commission() -> None:
    calc = USCostCalculator(slippage_ticks=0)
    cost = calc.calculate(price=100.0, quantity=10, side="BUY")
    assert cost.tax == 0.0
    assert cost.commission == 0.0


def test_us_cost_calculator_uses_one_cent_tick() -> None:
    calc = USCostCalculator(slippage_ticks=1)
    assert calc.get_tick_size(500.0) == pytest.approx(0.01, abs=1e-9)


def test_us_cost_does_not_apply_tw_minimum_commission() -> None:
    calc = USCostCalculator(commission_per_trade=0.0, slippage_ticks=0)
    cost = calc.calculate(price=1.0, quantity=1, side="BUY")
    assert cost.commission == 0.0


def test_tick_size_boundaries() -> None:
    calc = CostCalculator()

    assert calc.get_tick_size(9.99) == 0.01
    assert calc.get_tick_size(10.00) == 0.05
    assert calc.get_tick_size(49.99) == 0.05
    assert calc.get_tick_size(50.00) == 0.10
    assert calc.get_tick_size(99.99) == 0.10
    assert calc.get_tick_size(100.00) == 0.50
    assert calc.get_tick_size(499.99) == 0.50
    assert calc.get_tick_size(500.00) == 1.00
    assert calc.get_tick_size(999.99) == 1.00
    assert calc.get_tick_size(1000.00) == 5.00


def test_buy_no_tax() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=1000, quantity=100, side="BUY")

    assert cost.tax == 0.0


def test_sell_has_tax() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=1000, quantity=100, side="SELL")

    assert cost.tax == 300.0


def test_etf_tax_rate() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=1000, quantity=100, side="SELL", is_etf=True)

    assert cost.tax == 100.0


def test_commission_discount() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=1000, quantity=100, side="BUY")

    assert cost.commission == pytest.approx(85.5, abs=0.01)


def test_commission_minimum_20() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=1, quantity=10, side="BUY")

    assert cost.commission == 20.0


def test_slippage_buy() -> None:
    calc = CostCalculator()
    slipped_price = calc.apply_slippage(price=100, side="BUY")

    assert slipped_price == pytest.approx(100.5, abs=0.01)


def test_known_trade_total() -> None:
    calc = CostCalculator()
    cost = calc.calculate(price=500, quantity=1000, side="BUY")

    assert cost.commission == pytest.approx(427.5, abs=0.01)
    assert cost.tax == 0.0
    assert cost.slippage == pytest.approx(1000.0, abs=0.01)
    assert cost.total == pytest.approx(1427.5, abs=0.01)
