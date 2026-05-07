"""Unit tests for Phase 7-A: 6 new technical analysis strategies."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd
import pytest

from src.backtest.events import BarEvent, OrderEvent
from src.strategy.examples.bias import BiasStrategy
from src.strategy.examples.bollinger_band import BollingerBandStrategy
from src.strategy.examples.donchian_breakout import DonchianBreakoutStrategy
from src.strategy.examples.kd_cross import KDCrossStrategy
from src.strategy.examples.macd_cross import MACDCrossStrategy
from src.strategy.examples.rsi import RSIStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_SIGNAL_VALUES = {-1, 0, 1}


class _MockAccount:
    """Minimal account mock for on_bar tests."""

    def __init__(self, position: int = 0) -> None:
        self._position = position

    def get_position(self, symbol: str) -> int:  # noqa: ARG002
        return self._position

    def set_position(self, qty: int) -> None:
        self._position = qty


def _make_bar(close: float, i: int, high: float | None = None, low: float | None = None) -> BarEvent:
    from datetime import timedelta
    return BarEvent(
        symbol="TEST",
        timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc) + timedelta(days=i),
        open=close,
        high=high if high is not None else close + 0.5,
        low=low if low is not None else max(close - 0.5, 0.01),
        close=close,
        volume=1000,
        freq="1day",
    )


def _make_df(closes: list[float] | np.ndarray) -> pd.DataFrame:
    closes = np.asarray(closes, dtype="float64")
    n = len(closes)
    index = pd.date_range("2020-01-02", periods=n, freq="D", tz="UTC")
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes + 0.5,
            "low": np.maximum(closes - 0.5, 0.01),
            "close": closes,
            "volume": [1000] * n,
        },
        index=index,
    )


def _make_ohlcv_df(
    closes: list[float] | np.ndarray,
    highs: list[float] | np.ndarray | None = None,
    lows: list[float] | np.ndarray | None = None,
) -> pd.DataFrame:
    closes = np.asarray(closes, dtype="float64")
    n = len(closes)
    index = pd.date_range("2020-01-02", periods=n, freq="D", tz="UTC")
    _highs = np.asarray(highs, dtype="float64") if highs is not None else closes + 0.5
    _lows = np.asarray(lows, dtype="float64") if lows is not None else np.maximum(closes - 0.5, 0.01)
    return pd.DataFrame(
        {"open": closes, "high": _highs, "low": _lows, "close": closes, "volume": [1000] * n},
        index=index,
    )


def _v_shape_closes(n_flat: int = 20, n_decline: int = 15, n_recover: int = 20) -> np.ndarray:
    """Produce price series: flat → sharp decline → recovery."""
    flat = np.ones(n_flat) * 100.0
    decline = flat[-1] * (0.97 ** np.arange(1, n_decline + 1))
    recover = decline[-1] * (1.03 ** np.arange(1, n_recover + 1))
    return np.concatenate([flat, decline, recover])


def _feed_bars(strategy: Any, closes: np.ndarray, account: _MockAccount) -> list[list[OrderEvent]]:
    """Feed all bars to on_bar and return list of orders per bar."""
    all_orders = []
    for i, c in enumerate(closes):
        orders = strategy.on_bar(_make_bar(float(c), i), account)
        all_orders.append(orders)
        # Simulate position change from orders
        for o in orders:
            if o.side == "BUY":
                account.set_position(1000)
            elif o.side == "SELL":
                account.set_position(0)
    return all_orders


# ===========================================================================
# RSI Strategy
# ===========================================================================

def test_rsi_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        RSIStrategy(period=0)
    with pytest.raises(ValueError):
        RSIStrategy(oversold=70, overbought=30)
    with pytest.raises(ValueError):
        RSIStrategy(oversold=50, overbought=50)


def test_rsi_signal_values() -> None:
    closes = _v_shape_closes()
    df = _make_df(closes)
    strategy = RSIStrategy(period=14)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    # warm-up period must be zero
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_rsi_signal_correctness() -> None:
    closes = _v_shape_closes(n_flat=20, n_decline=15, n_recover=20)
    df = _make_df(closes)
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    signal = strategy.generate_signals(df)
    # Expect at least one buy signal in the recovery portion
    recovery_start = 20 + 15
    assert signal.iloc[recovery_start:].eq(1).any(), "Expected a +1 buy signal during RSI recovery"


def test_rsi_on_bar_produces_orders() -> None:
    closes = _v_shape_closes(n_flat=20, n_decline=15, n_recover=20)
    strategy = RSIStrategy(period=14, oversold=30, overbought=70)
    account = _MockAccount(position=0)
    all_orders = _feed_bars(strategy, closes, account)
    buy_orders = [o for orders in all_orders for o in orders if o.side == "BUY"]
    assert len(buy_orders) > 0, "Expected at least one BUY order from on_bar"


def test_rsi_reset_clears_state() -> None:
    closes = _v_shape_closes()
    strategy = RSIStrategy(period=14)
    account = _MockAccount(position=0)
    _feed_bars(strategy, closes, account)

    strategy.reset_runtime_state()
    assert strategy._close_history == []

    # After reset, on_bar with fewer bars than warmup_period should produce no orders
    orders = strategy.on_bar(_make_bar(100.0, 0), _MockAccount())
    assert orders == []


# ===========================================================================
# KD Cross Strategy
# ===========================================================================

def test_kd_cross_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        KDCrossStrategy(k_period=0)
    with pytest.raises(ValueError):
        KDCrossStrategy(d_period=0)
    with pytest.raises(ValueError):
        KDCrossStrategy(smooth_k=0)


def test_kd_cross_signal_values() -> None:
    closes = _v_shape_closes(n_flat=30, n_decline=20, n_recover=25)
    highs = closes + 1.0
    lows = np.maximum(closes - 1.0, 0.01)
    df = _make_ohlcv_df(closes, highs, lows)
    strategy = KDCrossStrategy(k_period=9, d_period=3, smooth_k=3)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_kd_cross_signal_correctness() -> None:
    closes = _v_shape_closes(n_flat=30, n_decline=20, n_recover=25)
    highs = closes + 2.0
    lows = np.maximum(closes - 2.0, 0.01)
    df = _make_ohlcv_df(closes, highs, lows)
    strategy = KDCrossStrategy(k_period=9, d_period=3, smooth_k=3)
    signal = strategy.generate_signals(df)
    # Expect at least one buy or sell signal
    assert signal.ne(0).any(), "Expected at least one non-zero signal"


def test_kd_cross_on_bar_produces_orders() -> None:
    closes = _v_shape_closes(n_flat=30, n_decline=20, n_recover=25)
    highs = closes + 2.0
    lows = np.maximum(closes - 2.0, 0.01)
    strategy = KDCrossStrategy(k_period=9, d_period=3, smooth_k=3)
    account = _MockAccount(position=0)
    all_orders: list[list[OrderEvent]] = []
    for i, (c, h, l) in enumerate(zip(closes, highs, lows)):
        bar = BarEvent(
            symbol="TEST",
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc) + timedelta(days=i),
            open=float(c),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=1000,
            freq="1day",
        )
        orders = strategy.on_bar(bar, account)
        all_orders.append(orders)
        for o in orders:
            account.set_position(1000 if o.side == "BUY" else 0)

    all_flat = [o for orders in all_orders for o in orders]
    assert len(all_flat) > 0, "Expected at least one order from KD on_bar"


def test_kd_cross_reset_clears_state() -> None:
    strategy = KDCrossStrategy()
    strategy._high_history = [100.0, 101.0]
    strategy._low_history = [99.0, 100.0]
    strategy._close_history = [100.0, 101.0]
    strategy.reset_runtime_state()
    assert strategy._high_history == []
    assert strategy._low_history == []
    assert strategy._close_history == []


# ===========================================================================
# MACD Cross Strategy
# ===========================================================================

def test_macd_cross_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        MACDCrossStrategy(fast=0)
    with pytest.raises(ValueError):
        MACDCrossStrategy(slow=0)
    with pytest.raises(ValueError):
        MACDCrossStrategy(signal=0)
    with pytest.raises(ValueError):
        MACDCrossStrategy(fast=30, slow=20)


def test_macd_cross_signal_values() -> None:
    closes = _v_shape_closes(n_flat=30, n_decline=15, n_recover=30)
    df = _make_df(closes)
    strategy = MACDCrossStrategy(fast=12, slow=26, signal=9)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_macd_cross_signal_correctness() -> None:
    # Build rising trend from declining baseline to trigger MACD golden cross
    base = np.ones(40) * 100.0
    rise = base[-1] * (1.015 ** np.arange(1, 41))
    closes = np.concatenate([base, rise])
    df = _make_df(closes)
    strategy = MACDCrossStrategy(fast=12, slow=26, signal=9)
    signal = strategy.generate_signals(df)
    assert signal.ne(0).any(), "Expected at least one MACD crossover signal"


def test_macd_cross_on_bar_produces_orders() -> None:
    base = np.ones(40) * 100.0
    rise = base[-1] * (1.015 ** np.arange(1, 41))
    closes = np.concatenate([base, rise])
    strategy = MACDCrossStrategy(fast=12, slow=26, signal=9)
    account = _MockAccount(position=0)
    all_orders = _feed_bars(strategy, closes, account)
    all_flat = [o for orders in all_orders for o in orders]
    assert len(all_flat) > 0, "Expected at least one order from MACD on_bar"


def test_macd_cross_reset_clears_state() -> None:
    strategy = MACDCrossStrategy()
    strategy._close_history = [100.0, 101.0, 102.0]
    strategy.reset_runtime_state()
    assert strategy._close_history == []


# ===========================================================================
# Bollinger Band Strategy
# ===========================================================================

def test_bollinger_band_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        BollingerBandStrategy(period=0)
    with pytest.raises(ValueError):
        BollingerBandStrategy(std_dev=0)
    with pytest.raises(ValueError):
        BollingerBandStrategy(std_dev=-1.0)


def test_bollinger_band_signal_values() -> None:
    # Oscillating prices around 100 with a sharp drop
    oscillate = 100 + np.sin(np.linspace(0, 4 * np.pi, 30)) * 3
    drop = oscillate[-1] * np.ones(5) * 0.85
    closes = np.concatenate([oscillate, drop, oscillate])
    df = _make_df(closes)
    strategy = BollingerBandStrategy(period=20, std_dev=2.0)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_bollinger_band_signal_correctness() -> None:
    # 25 bars oscillating ±3 around 100, then one big drop
    rng = np.random.default_rng(42)
    base = 100 + rng.uniform(-3, 3, 25)
    drop_val = float(base.mean() - 3 * base.std() * 1.5)  # well below lower band
    closes = np.concatenate([base, [drop_val]])
    df = _make_df(closes)
    strategy = BollingerBandStrategy(period=20, std_dev=2.0)
    signal = strategy.generate_signals(df)
    # The drop bar should trigger a buy signal
    assert signal.iloc[-1] == 1 or signal.eq(1).any(), "Expected a buy signal when price crosses below lower band"


def test_bollinger_band_on_bar_produces_orders() -> None:
    rng = np.random.default_rng(42)
    base = 100 + rng.uniform(-3, 3, 25)
    drop_val = float(base.mean() - 3 * base.std() * 1.5)
    closes = np.concatenate([base, [drop_val], base])
    strategy = BollingerBandStrategy(period=20, std_dev=2.0)
    account = _MockAccount(position=0)
    all_orders = _feed_bars(strategy, closes, account)
    all_flat = [o for orders in all_orders for o in orders]
    assert len(all_flat) > 0, "Expected at least one order from Bollinger Band on_bar"


def test_bollinger_band_reset_clears_state() -> None:
    strategy = BollingerBandStrategy()
    strategy._close_history = [100.0, 101.0]
    strategy.reset_runtime_state()
    assert strategy._close_history == []


# ===========================================================================
# Bias Strategy
# ===========================================================================

def test_bias_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        BiasStrategy(ma_period=0)
    with pytest.raises(ValueError):
        BiasStrategy(buy_bias=10.0, sell_bias=-10.0)
    with pytest.raises(ValueError):
        BiasStrategy(buy_bias=5.0, sell_bias=5.0)


def test_bias_signal_values() -> None:
    flat = np.ones(25) * 100.0
    drop = flat[-1] * (0.95 ** np.arange(1, 11))
    recover = drop[-1] * (1.03 ** np.arange(1, 16))
    closes = np.concatenate([flat, drop, recover])
    df = _make_df(closes)
    strategy = BiasStrategy(ma_period=20, buy_bias=-10.0, sell_bias=10.0)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_bias_signal_correctness() -> None:
    # 25 flat bars at 100, then single drop to 85 → BIAS = -15% < -10%
    flat = np.ones(25) * 100.0
    drop = np.array([85.0])
    closes = np.concatenate([flat, drop])
    df = _make_df(closes)
    strategy = BiasStrategy(ma_period=20, buy_bias=-10.0, sell_bias=10.0)
    signal = strategy.generate_signals(df)
    # The last bar should be a buy (BIAS crossed below -10%)
    assert signal.iloc[-1] == 1, f"Expected +1 buy at drop bar, got {signal.iloc[-1]}"


def test_bias_on_bar_produces_orders() -> None:
    flat = np.ones(25) * 100.0
    drop = np.ones(5) * 85.0
    recover = np.ones(10) * 100.0
    closes = np.concatenate([flat, drop, recover])
    strategy = BiasStrategy(ma_period=20, buy_bias=-10.0, sell_bias=10.0)
    account = _MockAccount(position=0)
    all_orders = _feed_bars(strategy, closes, account)
    buy_orders = [o for orders in all_orders for o in orders if o.side == "BUY"]
    assert len(buy_orders) > 0, "Expected at least one BUY order from Bias on_bar"


def test_bias_reset_clears_state() -> None:
    strategy = BiasStrategy()
    strategy._close_history = [100.0, 98.0, 97.0]
    strategy.reset_runtime_state()
    assert strategy._close_history == []


# ===========================================================================
# Donchian Breakout Strategy
# ===========================================================================

def test_donchian_invalid_params_raises() -> None:
    with pytest.raises(ValueError):
        DonchianBreakoutStrategy(entry_period=0)
    with pytest.raises(ValueError):
        DonchianBreakoutStrategy(exit_period=0)


def test_donchian_signal_values() -> None:
    base = np.ones(30) * 100.0
    spike = np.array([115.0])
    dip = np.array([85.0])
    closes = np.concatenate([base, spike, base, dip, base])
    highs = closes + 1.0
    lows = np.maximum(closes - 1.0, 0.01)
    df = _make_ohlcv_df(closes, highs, lows)
    strategy = DonchianBreakoutStrategy(entry_period=20, exit_period=10)
    signal = strategy.generate_signals(df)
    assert set(signal.unique()) <= _VALID_SIGNAL_VALUES
    assert (signal.iloc[: strategy.warmup_period] == 0).all()


def test_donchian_signal_correctness() -> None:
    # 25 bars at 100, then spike to 115 → breakout above previous 20-day high of 100
    base = np.ones(25) * 100.0
    spike = np.array([115.0])
    closes = np.concatenate([base, spike])
    highs = closes + 0.5
    lows = closes - 0.5
    df = _make_ohlcv_df(closes, highs, lows)
    strategy = DonchianBreakoutStrategy(entry_period=20, exit_period=10)
    signal = strategy.generate_signals(df)
    # spike bar index = 25; upper = max(high[5:25]) = 100.5
    # close at spike = 115 > 100.5 → buy signal
    assert signal.iloc[-1] == 1, f"Expected +1 buy at breakout bar, got {signal.iloc[-1]}"


def test_donchian_on_bar_produces_orders() -> None:
    base = np.ones(25) * 100.0
    spike = np.ones(5) * 115.0
    closes = np.concatenate([base, spike])
    highs = closes + 0.5
    lows = np.maximum(closes - 0.5, 0.01)
    strategy = DonchianBreakoutStrategy(entry_period=20, exit_period=10)
    account = _MockAccount(position=0)
    all_orders: list[list[OrderEvent]] = []
    for i, (c, h, l) in enumerate(zip(closes, highs, lows)):
        bar = BarEvent(
            symbol="TEST",
            timestamp=datetime(2024, 1, 2, tzinfo=timezone.utc) + timedelta(days=i),
            open=float(c),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=1000,
            freq="1day",
        )
        orders = strategy.on_bar(bar, account)
        all_orders.append(orders)
        for o in orders:
            account.set_position(1000 if o.side == "BUY" else 0)

    buy_orders = [o for orders in all_orders for o in orders if o.side == "BUY"]
    assert len(buy_orders) > 0, "Expected at least one BUY order from Donchian on_bar"


def test_donchian_reset_clears_state() -> None:
    strategy = DonchianBreakoutStrategy()
    strategy._high_history = [100.0, 101.0]
    strategy._low_history = [99.0, 100.0]
    strategy._close_history = [100.0, 101.0]
    strategy.reset_runtime_state()
    assert strategy._high_history == []
    assert strategy._low_history == []
    assert strategy._close_history == []
