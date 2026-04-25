from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.backtest.engine_vec import VectorizedBacktester
from src.strategy.base import StrategyBase
from src.strategy.examples.ma_cross import MACrossStrategy


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ma_cross_data.csv"


def _load_fixture() -> pd.DataFrame:
    df = pd.read_csv(FIXTURE_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")


def _build_hand_calculated_fixture() -> pd.DataFrame:
    index = pd.date_range("2024-01-02", periods=6, freq="D")
    return pd.DataFrame(
        {
            "open": [100.0, 101.0, 103.0, 106.0, 107.0, 109.0],
            "high": [101.0, 103.0, 104.0, 107.0, 109.0, 110.0],
            "low": [99.0, 100.0, 102.0, 104.0, 106.0, 108.0],
            "close": [100.0, 102.0, 104.0, 105.0, 108.0, 110.0],
            "symbol": ["2330"] * 6,
        },
        index=index,
    )


class _DeterministicStrategy(StrategyBase):
    def __init__(self, signals: list[int]) -> None:
        self._signals = signals

    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        if len(df) != len(self._signals):
            raise ValueError("Signal length must match dataframe length.")
        return pd.Series(self._signals, index=df.index, dtype="int8")

    def on_bar(self, bar, account) -> list:
        _ = (bar, account)
        return []


def test_ma_cross_signal_golden_cross() -> None:
    df = _load_fixture()
    strategy = MACrossStrategy(ma_short=20, ma_long=60)
    signal = strategy.generate_signals(df)

    known_golden_cross_date = pd.Timestamp("2024-04-01")
    assert signal.loc[known_golden_cross_date] == 1


def test_ma_cross_signal_no_lookahead() -> None:
    df = _load_fixture()
    strategy = MACrossStrategy(ma_short=20, ma_long=60)
    full_signal = strategy.generate_signals(df)

    for i in range(len(df)):
        partial_signal = strategy.generate_signals(df.iloc[: i + 1])
        assert partial_signal.iloc[-1] == full_signal.iloc[i]


def test_ma_cross_signal_alignment() -> None:
    df = _load_fixture()
    strategy = MACrossStrategy(ma_short=20, ma_long=60)
    signal = strategy.generate_signals(df)

    assert signal.index.equals(df.index)
    assert len(signal) == len(df)


def test_signal_values_only_minus1_0_plus1() -> None:
    df = _load_fixture()
    strategy = MACrossStrategy(ma_short=20, ma_long=60)
    signal = strategy.generate_signals(df)

    assert not signal.isna().any()
    assert set(signal.unique().tolist()).issubset({-1, 0, 1})


def test_vectorized_backtest_basic() -> None:
    df = _load_fixture()
    strategy = MACrossStrategy(ma_short=20, ma_long=60)
    backtester = VectorizedBacktester(initial_capital=1_000_000)

    result = backtester.run(strategy, df)

    assert result.total_trades > 0
    assert len(result.equity_curve) == len(df)


def test_vectorized_backtest_hand_calculated_fixture() -> None:
    df = _build_hand_calculated_fixture()
    strategy = _DeterministicStrategy(signals=[1, 0, 0, -1, 0, 0])
    backtester = VectorizedBacktester(initial_capital=1_000_000)

    result = backtester.run(strategy, df)

    assert result.total_trades == 1
    assert len(result.equity_curve) == len(df)

    trade = result.trades.iloc[0]
    assert pd.Timestamp(trade["entry_date"]) == df.index[1]
    assert pd.Timestamp(trade["exit_date"]) == df.index[4]
    assert float(trade["entry_price"]) == pytest.approx(101.0, abs=1e-9)
    assert float(trade["exit_price"]) == pytest.approx(107.0, abs=1e-9)
    assert float(trade["pnl"]) == pytest.approx(40_510.44, abs=1e-6)

    assert result.equity_curve.loc[df.index[1]] == pytest.approx(1_003_722.805, abs=1e-6)
    assert result.equity_curve.loc[df.index[2]] == pytest.approx(1_021_722.805, abs=1e-6)
    assert result.equity_curve.loc[df.index[3]] == pytest.approx(1_030_722.805, abs=1e-6)
    assert result.equity_curve.loc[df.index[4]] == pytest.approx(1_040_510.44, abs=1e-6)
    assert result.equity_curve.iloc[-1] == pytest.approx(1_040_510.44, abs=1e-6)
    assert result.equity_curve.iloc[-1] == pytest.approx(1_000_000 + float(trade["pnl"]), abs=1e-6)
