from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pytest

from src.backtest.cost import CostCalculator
from src.backtest.engine_event import EventDrivenBacktester
from src.backtest.events import FillEvent, OrderEvent
from src.strategy.base import StrategyBase


def _build_data(rows: int = 8) -> pd.DataFrame:
    index = pd.date_range("2024-01-02 09:00", periods=rows, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0][:rows],
            "high": [101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0][:rows],
            "low": [99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0][:rows],
            "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 106.5, 107.5][:rows],
            "volume": [1000] * rows,
            "symbol": ["2330"] * rows,
        },
        index=index,
    )


@dataclass
class CountingStrategy(StrategyBase):
    call_count: int = 0

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(0, index=df.index, dtype="int8")

    def on_bar(self, bar, account) -> list[OrderEvent]:
        _ = (bar, account)
        self.call_count += 1
        return []


@dataclass
class SingleOrderStrategy(StrategyBase):
    trigger_index: int
    side: str = "BUY"
    call_index: int = 0
    fills: list[FillEvent] = field(default_factory=list)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(0, index=df.index, dtype="int8")

    def on_bar(self, bar, account) -> list[OrderEvent]:
        _ = account
        orders: list[OrderEvent] = []
        if self.call_index == self.trigger_index:
            orders.append(
                OrderEvent(
                    symbol=bar.symbol,
                    order_type="MARKET",
                    side=self.side,
                    quantity=1000,
                )
            )
        self.call_index += 1
        return orders

    def on_fill(self, fill, account) -> None:
        _ = account
        self.fills.append(fill)


@dataclass
class NoFutureStrategy(StrategyBase):
    expected_close: list[float]
    call_index: int = 0
    positions_seen: list[int] = field(default_factory=list)

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(0, index=df.index, dtype="int8")

    def on_bar(self, bar, account) -> list[OrderEvent]:
        assert bar.close == pytest.approx(self.expected_close[self.call_index], abs=1e-9)
        self.positions_seen.append(account.get_position(bar.symbol))

        orders: list[OrderEvent] = []
        if self.call_index == 0:
            orders.append(
                OrderEvent(
                    symbol=bar.symbol,
                    order_type="MARKET",
                    side="BUY",
                    quantity=1000,
                )
            )
        self.call_index += 1
        return orders


def test_on_bar_called_per_bar() -> None:
    df = _build_data()
    strategy = CountingStrategy()
    backtester = EventDrivenBacktester(initial_capital=1_000_000)

    backtester.run(strategy, df)

    assert strategy.call_count == len(df)


def test_order_filled_next_bar() -> None:
    df = _build_data()
    strategy = SingleOrderStrategy(trigger_index=2, side="BUY")
    backtester = EventDrivenBacktester(initial_capital=1_000_000)

    backtester.run(strategy, df)

    assert len(strategy.fills) == 1
    assert pd.Timestamp(strategy.fills[0].timestamp) == df.index[3]


def test_market_order_fill_price() -> None:
    df = _build_data()
    calc = CostCalculator(slippage_ticks=1)
    strategy = SingleOrderStrategy(trigger_index=0, side="BUY")
    backtester = EventDrivenBacktester(initial_capital=1_000_000, cost_calculator=calc)

    backtester.run(strategy, df)

    expected = calc.apply_slippage(price=float(df.iloc[1]["open"]), side="BUY")
    assert len(strategy.fills) == 1
    assert strategy.fills[0].fill_price == pytest.approx(expected, abs=1e-9)


def test_no_future_function() -> None:
    df = _build_data()
    strategy = NoFutureStrategy(expected_close=df["close"].tolist())
    backtester = EventDrivenBacktester(initial_capital=1_000_000)

    backtester.run(strategy, df)

    assert strategy.call_index == len(df)
    assert strategy.positions_seen[0] == 0
    assert strategy.positions_seen[1] > 0


def test_equity_curve_length() -> None:
    df = _build_data()
    strategy = CountingStrategy()
    backtester = EventDrivenBacktester(initial_capital=1_000_000)

    result = backtester.run(strategy, df)
    assert len(result.equity_curve) == len(df)


def test_last_bar_pending_orders_discarded() -> None:
    df = _build_data()
    strategy = SingleOrderStrategy(trigger_index=len(df) - 1, side="BUY")
    backtester = EventDrivenBacktester(initial_capital=1_000_000)

    result = backtester.run(strategy, df)

    assert len(strategy.fills) == 0
    assert result.total_trades == 0
    assert result.equity_curve.iloc[-1] == pytest.approx(1_000_000.0, abs=1e-9)
