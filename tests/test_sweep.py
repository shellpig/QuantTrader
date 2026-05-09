"""Tests for src/backtest/sweep.py (Phase 7-C)."""

from __future__ import annotations

import unittest.mock as mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtest.sweep import (
    MAX_COMBOS,
    SWEEP_PARAM_SPECS,
    SweepResult,
    SweepRunSummary,
    generate_param_grid,
    parse_param_values,
    run_parameter_sweep,
    save_sweep_result_csv,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

def _synthetic_data(n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    dates = pd.date_range("2022-01-01", periods=n, freq="B", tz="Asia/Taipei")
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


# ---------------------------------------------------------------------------
# parse_param_values
# ---------------------------------------------------------------------------

def test_parse_param_values_integers() -> None:
    assert parse_param_values("5,10,20") == [5.0, 10.0, 20.0]


def test_parse_param_values_floats() -> None:
    result = parse_param_values("1.5,2.0,2.5")
    assert result == pytest.approx([1.5, 2.0, 2.5])


def test_parse_param_values_negative() -> None:
    result = parse_param_values("-15,-10,-5")
    assert result == pytest.approx([-15.0, -10.0, -5.0])


def test_parse_param_values_single() -> None:
    assert parse_param_values("14") == [14.0]


def test_parse_param_values_empty_string() -> None:
    assert parse_param_values("") == []


def test_parse_param_values_invalid() -> None:
    assert parse_param_values("abc,def") == []


def test_parse_param_values_whitespace() -> None:
    assert parse_param_values(" 5 , 10 , 20 ") == [5.0, 10.0, 20.0]


def test_parse_param_values_dedup_sort() -> None:
    assert parse_param_values("20,5,10,10") == [5.0, 10.0, 20.0]


def test_parse_param_values_sort_only() -> None:
    assert parse_param_values("30,10,20") == [10.0, 20.0, 30.0]


# ---------------------------------------------------------------------------
# generate_param_grid
# ---------------------------------------------------------------------------

def test_generate_param_grid_ma_cross_all_valid() -> None:
    # Acceptance criterion: short=[5,10,20] × long=[40,60,120] → 9 combos, all valid
    total, valid = generate_param_grid(
        "moving_average_cross",
        {"short_window": [5, 10, 20], "long_window": [40, 60, 120]},
    )
    assert total == 9
    assert len(valid) == 9


def test_generate_param_grid_ma_cross_filters_invalid() -> None:
    # short >= long should be excluded
    total, valid = generate_param_grid(
        "moving_average_cross",
        {"short_window": [5, 20, 50], "long_window": [10, 30]},
    )
    assert total == 6
    # Valid: (5,10), (5,30), (20,30) — short=50 invalid for both, short=20,long=10 invalid
    assert len(valid) == 3
    for combo in valid:
        assert combo["short_window"] < combo["long_window"]


def test_generate_param_grid_rsi_filters_invalid() -> None:
    # oversold >= overbought should be excluded
    total, valid = generate_param_grid(
        "rsi",
        {"period": [14], "oversold": [30, 70], "overbought": [70, 80]},
    )
    assert total == 4
    # Invalid: oversold=70, overbought=70 (equal); Valid: (30,70), (30,80), (70,80) = 3
    assert len(valid) == 3
    for combo in valid:
        assert combo["oversold"] < combo["overbought"]


def test_generate_param_grid_macd_cross_filters_invalid() -> None:
    total, valid = generate_param_grid(
        "macd_cross",
        {"fast": [12, 26], "slow": [26], "signal": [9]},
    )
    assert total == 2
    # fast=26, slow=26 → invalid (fast >= slow)
    assert len(valid) == 1
    assert valid[0]["fast"] == 12


def test_generate_param_grid_bias_filters_invalid() -> None:
    total, valid = generate_param_grid(
        "bias",
        {"ma_period": [20], "buy_bias": [-10, 5], "sell_bias": [10]},
    )
    assert total == 2
    # buy_bias=5 >= sell_bias=10 is False (5 < 10 valid), buy_bias=-10 < sell_bias=10 valid
    # Actually both are valid: -10 < 10 and 5 < 10
    assert len(valid) == 2


def test_generate_param_grid_unknown_strategy_returns_all() -> None:
    total, valid = generate_param_grid(
        "unknown_strategy",
        {"param_a": [1, 2], "param_b": [3, 4]},
    )
    assert total == 4
    assert len(valid) == 4


def test_generate_param_grid_max_combos_constant() -> None:
    assert MAX_COMBOS == 200


def test_sweep_param_specs_excludes_dca() -> None:
    assert "dollar_cost_averaging" not in SWEEP_PARAM_SPECS
    assert len(SWEEP_PARAM_SPECS) == 7


# ---------------------------------------------------------------------------
# run_parameter_sweep — combo limit
# ---------------------------------------------------------------------------

def test_run_parameter_sweep_exceeds_limit_raises() -> None:
    # 15 × 15 = 225 valid combos (all short < long) → exceeds MAX_COMBOS=200
    short_vals = list(range(1, 16))   # [1 .. 15]
    long_vals = list(range(16, 31))   # [16 .. 30]
    with pytest.raises(ValueError, match="超過上限"):
        run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": short_vals, "long_window": long_vals},
        )


# ---------------------------------------------------------------------------
# run_parameter_sweep
# ---------------------------------------------------------------------------

def _make_mock_bt_result(**overrides):
    result = mock.MagicMock()
    result.total_return = overrides.get("total_return", 0.1)
    result.annual_return = overrides.get("annual_return", 0.05)
    result.max_drawdown = overrides.get("max_drawdown", 0.1)
    result.sharpe_ratio = overrides.get("sharpe_ratio", 1.2)
    result.win_rate = overrides.get("win_rate", 0.55)
    result.profit_factor = overrides.get("profit_factor", 1.5)
    result.total_trades = overrides.get("total_trades", 15)
    return result


def test_run_parameter_sweep_correct_combo_count() -> None:
    mock_result = _make_mock_bt_result()

    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5, 10], "long_window": [20, 40]},
        )

    # All 4 combos are valid (5<20, 5<40, 10<20, 10<40)
    assert sweep.total_combos == 4
    assert sweep.valid_combos == 4
    assert len(sweep.results) == 4
    assert all(s.error is None for s in sweep.results)


def test_run_parameter_sweep_filters_invalid_combos() -> None:
    mock_result = _make_mock_bt_result()

    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5, 20, 50], "long_window": [10, 30]},
        )

    assert sweep.total_combos == 6
    assert sweep.valid_combos == 3
    assert len(sweep.results) == 3
    # Engine only called for valid combos
    assert mock_engine.run.call_count == 3


def test_run_parameter_sweep_captures_errors() -> None:
    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.side_effect = RuntimeError("回測失敗")
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5], "long_window": [20]},
        )

    assert len(sweep.results) == 1
    s = sweep.results[0]
    assert s.error is not None
    assert "回測失敗" in s.error
    assert s.total_trades == 0


def test_run_parameter_sweep_result_fields() -> None:
    mock_result = _make_mock_bt_result(total_return=0.25, sharpe_ratio=1.8, total_trades=5)

    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5], "long_window": [20]},
        )

    s = sweep.results[0]
    assert s.total_return == pytest.approx(0.25)
    assert s.sharpe_ratio == pytest.approx(1.8)
    assert s.total_trades == 5
    assert s.params == {"short_window": 5.0, "long_window": 20.0}
    # sample_warning: trades=5 >= 3 → False
    assert s.sample_warning is False
    # result stored on the summary object
    assert s.result is mock_result


def test_run_parameter_sweep_sample_warning_set_when_few_trades() -> None:
    mock_result = _make_mock_bt_result(total_trades=2)  # < 3 → warning

    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5], "long_window": [20]},
        )

    assert sweep.results[0].sample_warning is True


def test_run_parameter_sweep_error_result_is_none() -> None:
    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.side_effect = RuntimeError("boom")
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-01",
            end_date="2022-12-31",
            strategy_type="moving_average_cross",
            param_candidates={"short_window": [5], "long_window": [20]},
        )

    s = sweep.results[0]
    assert s.error is not None
    assert s.result is None
    assert s.sample_warning is False


def test_run_parameter_sweep_metadata() -> None:
    mock_result = _make_mock_bt_result()

    with mock.patch("src.backtest.sweep.VectorizedBacktester") as mock_engine_cls:
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = mock_result
        mock_engine_cls.return_value = mock_engine

        sweep = run_parameter_sweep(
            data=_synthetic_data(),
            symbol="2330",
            start_date="2022-01-03",
            end_date="2022-12-30",
            strategy_type="rsi",
            param_candidates={"period": [14], "oversold": [30], "overbought": [70]},
        )

    assert sweep.symbol == "2330"
    assert sweep.start_date == "2022-01-03"
    assert sweep.end_date == "2022-12-30"
    assert sweep.strategy_type == "rsi"


# ---------------------------------------------------------------------------
# save_sweep_result_csv
# ---------------------------------------------------------------------------

def test_save_sweep_result_csv_creates_file(tmp_path: Path) -> None:
    sweep = SweepResult(
        symbol="2330",
        start_date="2022-01-01",
        end_date="2022-12-31",
        strategy_type="moving_average_cross",
        total_combos=4,
        valid_combos=4,
        results=[
            SweepRunSummary(
                params={"short_window": 5, "long_window": 20},
                total_return=0.10,
                annual_return=0.05,
                max_drawdown=0.08,
                sharpe_ratio=1.2,
                win_rate=0.55,
                profit_factor=1.5,
                total_trades=12,
                error=None,
            ),
            SweepRunSummary(
                params={"short_window": 5, "long_window": 40},
                total_return=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                error="test error",
            ),
        ],
    )

    with mock.patch("src.backtest.sweep.Path", side_effect=lambda p: tmp_path / Path(p).name if p == "data/backtest/parameter_sweeps" else Path(p)):
        saved = save_sweep_result_csv(sweep)

    assert saved.exists()
    df = pd.read_csv(saved, encoding="utf-8-sig")
    assert "short_window" in df.columns
    assert "long_window" in df.columns
    assert "Sharpe" in df.columns
    assert "sample_warning" in df.columns
    assert len(df) == 2


def test_save_sweep_result_csv_sample_warning_flag(tmp_path: Path) -> None:
    sweep = SweepResult(
        symbol="2330",
        start_date="2022-01-01",
        end_date="2022-12-31",
        strategy_type="rsi",
        total_combos=2,
        valid_combos=2,
        results=[
            SweepRunSummary(
                params={"period": 14, "oversold": 30, "overbought": 70},
                total_return=0.05,
                annual_return=0.03,
                max_drawdown=0.05,
                sharpe_ratio=0.8,
                win_rate=0.5,
                profit_factor=1.2,
                total_trades=2,
                error=None,
                sample_warning=True,   # total_trades < 3
            ),
            SweepRunSummary(
                params={"period": 21, "oversold": 30, "overbought": 70},
                total_return=0.12,
                annual_return=0.06,
                max_drawdown=0.1,
                sharpe_ratio=1.5,
                win_rate=0.6,
                profit_factor=1.8,
                total_trades=10,
                error=None,
                sample_warning=False,
            ),
        ],
    )

    with mock.patch("src.backtest.sweep.Path", side_effect=lambda p: tmp_path / Path(p).name if p == "data/backtest/parameter_sweeps" else Path(p)):
        saved = save_sweep_result_csv(sweep)

    df = pd.read_csv(saved, encoding="utf-8-sig")
    assert df.loc[0, "sample_warning"] == True  # noqa: E712
    assert df.loc[1, "sample_warning"] == False  # noqa: E712


def test_save_sweep_result_csv_profit_factor_sentinel(tmp_path: Path) -> None:
    sweep = SweepResult(
        symbol="2330",
        start_date="2022-01-01",
        end_date="2022-12-31",
        strategy_type="bollinger_band",
        total_combos=1,
        valid_combos=1,
        results=[
            SweepRunSummary(
                params={"period": 20, "std_dev": 2.0},
                total_return=0.05,
                annual_return=0.03,
                max_drawdown=0.05,
                sharpe_ratio=0.8,
                win_rate=1.0,
                profit_factor=999.0,  # sentinel → N/A
                total_trades=5,
                error=None,
            ),
        ],
    )

    with mock.patch("src.backtest.sweep.Path", side_effect=lambda p: tmp_path / Path(p).name if p == "data/backtest/parameter_sweeps" else Path(p)):
        saved = save_sweep_result_csv(sweep)

    df = pd.read_csv(saved, encoding="utf-8-sig", keep_default_na=False)
    assert df.loc[0, "Profit Factor"] == "N/A"


# ---------------------------------------------------------------------------
# Integration: real backtest (no mocks)
# ---------------------------------------------------------------------------

def test_run_parameter_sweep_real_ma_cross() -> None:
    """Acceptance criterion: MA Cross sweep correctly excludes short >= long combos."""
    data = _synthetic_data(n=400)

    sweep = run_parameter_sweep(
        data=data,
        symbol="2330",
        start_date="2022-01-01",
        end_date="2023-06-30",
        strategy_type="moving_average_cross",
        param_candidates={"short_window": [5, 10, 20], "long_window": [40, 60, 120]},
    )

    assert sweep.total_combos == 9
    assert sweep.valid_combos == 9  # all short < long
    assert len(sweep.results) == 9
    # No invalid-param combos got through
    for s in sweep.results:
        if s.error is None:
            assert s.params["short_window"] < s.params["long_window"]
