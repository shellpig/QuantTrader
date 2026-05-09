"""Tests for src/backtest/batch.py (Phase 7-B)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtest.batch import (
    BatchResult,
    StrategyRunSummary,
    _build_strategy,
    run_strategy_batch,
    save_batch_result_csv,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _synthetic_data(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-01", periods=n, freq="B")
    close = 500.0 + np.cumsum(rng.standard_normal(n) * 3)
    open_ = close * (1 + rng.standard_normal(n) * 0.003)
    high = close * (1 + np.abs(rng.standard_normal(n) * 0.008))
    low = close * (1 - np.abs(rng.standard_normal(n) * 0.008))
    return pd.DataFrame({
        "date": dates,
        "symbol": "2330",
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": rng.integers(1000, 10000, n),
    })


_VALID_PRESETS = [
    {"name": "MA20_MA60", "type": "moving_average_cross", "params": {"short_window": 20, "long_window": 60}},
    {"name": "RSI_14",    "type": "rsi",                  "params": {"period": 14, "oversold": 30.0, "overbought": 70.0}},
    {"name": "MACD_Cross","type": "macd_cross",            "params": {"fast": 12, "slow": 26, "signal": 9}},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_run_strategy_batch_returns_all_summaries() -> None:
    data = _synthetic_data()
    batch = run_strategy_batch(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-03-01",
        presets=_VALID_PRESETS,
    )
    assert isinstance(batch, BatchResult)
    assert len(batch.summaries) == 3


def test_run_strategy_batch_failed_preset_skipped() -> None:
    bad_preset = {
        "name": "Bad_MA",
        "type": "moving_average_cross",
        # short_window >= long_window → will raise in MACrossStrategy constructor
        "params": {"short_window": 60, "long_window": 20},
    }
    presets = [_VALID_PRESETS[0], bad_preset]
    data = _synthetic_data()
    batch = run_strategy_batch(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-03-01",
        presets=presets,
    )
    assert len(batch.summaries) == 2

    good = batch.summaries[0]
    assert good.error is None
    assert good.result is not None

    bad = batch.summaries[1]
    assert bad.error is not None
    assert bad.result is None


def test_run_strategy_batch_summary_fields_correct() -> None:
    from src.backtest.engine_vec import VectorizedBacktester
    from src.strategy.examples.rsi import RSIStrategy

    data = _synthetic_data()
    preset = {"name": "RSI_14", "type": "rsi", "params": {"period": 14, "oversold": 30.0, "overbought": 70.0}}
    batch = run_strategy_batch(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-03-01",
        presets=[preset],
    )
    summary = batch.summaries[0]
    assert summary.error is None
    assert summary.result is not None

    # Verify key fields match a direct single run
    engine = VectorizedBacktester()
    direct = engine.run(strategy=RSIStrategy(period=14, oversold=30, overbought=70), data=data)

    assert abs(summary.total_return - direct.total_return) < 1e-9
    assert abs(summary.sharpe_ratio - direct.sharpe_ratio) < 1e-9
    assert summary.total_trades == direct.total_trades


def test_batch_result_signals_exposed() -> None:
    data = _synthetic_data()
    batch = run_strategy_batch(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-03-01",
        presets=[_VALID_PRESETS[0]],
    )
    summary = batch.summaries[0]
    assert summary.result is not None
    assert summary.result.signals is not None
    assert isinstance(summary.result.signals, pd.Series)
    assert len(summary.result.signals) > 0


def test_save_comparison_csv_creates_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from src.backtest import batch as batch_module

    monkeypatch.setattr(batch_module, "Path", lambda *a, **kw: tmp_path / Path(*a, **kw).name if len(a) == 1 else Path(*a, **kw))

    data = _synthetic_data()
    batch = run_strategy_batch(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-03-01",
        presets=[_VALID_PRESETS[0]],
    )

    # Use tmp_path directly to avoid writing to project tree
    from src.backtest.batch import save_batch_result_csv
    import unittest.mock as mock
    out_dir = tmp_path / "strategy_comparisons"
    with mock.patch("src.backtest.batch.Path", side_effect=lambda p: out_dir if p == "data/backtest/strategy_comparisons" else Path(p)):
        saved = save_batch_result_csv(batch)

    assert saved.exists()
    df = pd.read_csv(saved, encoding="utf-8-sig")
    expected_cols = {"策略名稱", "策略類型", "總報酬", "年化報酬", "最大回撤", "Sharpe", "勝率", "Profit Factor", "交易次數", "錯誤"}
    assert expected_cols.issubset(set(df.columns))


def test_build_strategy_all_types() -> None:
    types_and_params = [
        ("moving_average_cross", {"short_window": 20, "long_window": 60}),
        ("rsi",                  {"period": 14, "oversold": 30.0, "overbought": 70.0}),
        ("kd_cross",             {"k_period": 9, "d_period": 3, "smooth_k": 3}),
        ("macd_cross",           {"fast": 12, "slow": 26, "signal": 9}),
        ("bollinger_band",       {"period": 20, "std_dev": 2.0}),
        ("bias",                 {"ma_period": 20, "buy_bias": -10.0, "sell_bias": 10.0}),
        ("donchian_breakout",    {"entry_period": 20, "exit_period": 10}),
    ]
    for strategy_type, params in types_and_params:
        strategy = _build_strategy(strategy_type, params)
        assert strategy is not None, f"Failed to build strategy: {strategy_type}"


def test_build_strategy_unsupported_type_raises() -> None:
    with pytest.raises(ValueError, match="不支援的策略類型"):
        _build_strategy("unknown_strategy", {})
