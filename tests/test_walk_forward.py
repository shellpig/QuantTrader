"""Tests for src/backtest/walk_forward.py (Phase 7-D-1)."""

from __future__ import annotations

import unittest.mock as mock
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.backtest.sweep import SweepResult, SweepRunSummary
from src.backtest.walk_forward import (
    MAX_WFA_WINDOWS,
    MIN_OOS_TRADES_WARNING,
    MIN_WFA_WINDOWS,
    SUPPORTED_OPTIMIZE_METRICS,
    WalkForwardSummary,
    WalkForwardWindow,
    WalkForwardWindowResult,
    calculate_parameter_stability,
    generate_walk_forward_windows,
    required_months_for_wfa,
    run_walk_forward_analysis,
    save_walk_forward_summary_csv,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(n_months: int, start: str = "2020-01-01") -> pd.DataFrame:
    """Synthetic daily OHLCV data with timezone-aware DatetimeIndex."""
    n_days = n_months * 22
    rng = np.random.default_rng(42)
    dates = pd.date_range(start, periods=n_days, freq="B", tz="Asia/Taipei")
    close = 100.0 + np.cumsum(rng.standard_normal(n_days) * 2)
    close = np.maximum(close, 1.0)
    return pd.DataFrame(
        {
            "open": close * 0.99,
            "high": close * 1.01,
            "low": close * 0.98,
            "close": close,
            "volume": rng.integers(1000, 10000, n_days),
        },
        index=dates,
    )


def _make_sweep_run(
    params: dict,
    *,
    total_return: float = 0.05,
    annual_return: float = 0.03,
    sharpe_ratio: float = 1.0,
    total_trades: int = 10,
    error: str | None = None,
) -> SweepRunSummary:
    result: mock.MagicMock | None
    if error is None:
        result = mock.MagicMock()
        result.total_return = total_return
        result.annual_return = annual_return
        result.max_drawdown = 0.05
        result.sharpe_ratio = sharpe_ratio
        result.win_rate = 0.55
        result.profit_factor = 1.5
        result.total_trades = total_trades
    else:
        result = None
    return SweepRunSummary(
        params=params,
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=0.05,
        sharpe_ratio=sharpe_ratio,
        win_rate=0.55,
        profit_factor=1.5,
        total_trades=total_trades,
        error=error,
        result=result,
    )


def _make_sweep_result(runs: list[SweepRunSummary]) -> SweepResult:
    return SweepResult(
        symbol="2330",
        start_date="2020-01-01",
        end_date="2020-12-31",
        strategy_type="moving_average_cross",
        total_combos=len(runs),
        valid_combos=len(runs),
        results=runs,
    )


def _make_oos_result(
    *,
    total_return: float = 0.03,
    annual_return: float = 0.02,
    sharpe_ratio: float = 0.8,
    max_drawdown: float = 0.05,
    total_trades: int = 10,
) -> mock.MagicMock:
    r = mock.MagicMock()
    r.total_return = total_return
    r.annual_return = annual_return
    r.max_drawdown = max_drawdown
    r.sharpe_ratio = sharpe_ratio
    r.total_trades = total_trades
    return r


def _make_wf_window(window_id: int = 0) -> WalkForwardWindow:
    return WalkForwardWindow(
        window_id=window_id,
        is_start=pd.Timestamp("2020-01-01", tz="Asia/Taipei"),
        is_end=pd.Timestamp("2020-12-31", tz="Asia/Taipei"),
        oos_start=pd.Timestamp("2021-01-01", tz="Asia/Taipei"),
        oos_end=pd.Timestamp("2021-06-30", tz="Asia/Taipei"),
    )


def _make_wf_result(
    params: dict | None,
    *,
    skipped: bool = False,
    degradation: float | None = None,
    oos_result=None,
    warnings: list[str] | None = None,
) -> WalkForwardWindowResult:
    return WalkForwardWindowResult(
        window=_make_wf_window(),
        best_params=params,
        is_best=None,
        oos_result=oos_result,
        degradation=degradation,
        skipped=skipped,
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# required_months_for_wfa
# ---------------------------------------------------------------------------

def test_required_months_for_wfa_formula() -> None:
    # is=12, oos=6, step=6, min_windows=3 → 12 + 6 + 2*6 = 30
    assert required_months_for_wfa(is_months=12, oos_months=6, step_months=6) == 30


def test_required_months_for_wfa_custom() -> None:
    # is=3, oos=2, step=2, min_windows=3 → 3 + 2 + 2*2 = 9
    assert required_months_for_wfa(is_months=3, oos_months=2, step_months=2, min_windows=3) == 9


def test_required_months_for_wfa_single_window() -> None:
    # min_windows=1 → is + oos
    assert required_months_for_wfa(is_months=6, oos_months=3, step_months=3, min_windows=1) == 9


# ---------------------------------------------------------------------------
# generate_walk_forward_windows
# ---------------------------------------------------------------------------

def test_generate_walk_forward_windows_basic() -> None:
    # 10 months of data, is=3, oos=2, step=2 → 3 + 2 + (3-1)*2 = 9 months needed → fits
    data = _make_data(10)
    windows = generate_walk_forward_windows(
        data, is_months=3, oos_months=2, step_months=2, min_windows=3
    )
    assert len(windows) >= 3
    for i, win in enumerate(windows):
        assert win.window_id == i
        assert win.is_start <= win.is_end
        assert win.oos_start <= win.oos_end
        assert win.is_end < win.oos_start


def test_generate_walk_forward_windows_no_overlap() -> None:
    data = _make_data(12)
    windows = generate_walk_forward_windows(
        data, is_months=3, oos_months=2, step_months=2
    )
    for i in range(len(windows) - 1):
        # consecutive windows: IS of next starts after step from current IS start
        assert windows[i].is_start < windows[i + 1].is_start


def test_generate_walk_forward_windows_requires_enough_data() -> None:
    # Only 5 months, need 9 months
    data = _make_data(5)
    with pytest.raises(ValueError, match="資料長度不足"):
        generate_walk_forward_windows(
            data, is_months=3, oos_months=2, step_months=2, min_windows=3
        )


def test_generate_walk_forward_windows_error_message_format() -> None:
    data = _make_data(5)
    with pytest.raises(ValueError, match=r"IS \d+ \+ OOS \d+"):
        generate_walk_forward_windows(
            data, is_months=3, oos_months=2, step_months=2
        )


def test_generate_walk_forward_windows_max_windows_cap() -> None:
    # 60 months would produce > 10 windows — capped at MAX_WFA_WINDOWS
    data = _make_data(60)
    windows = generate_walk_forward_windows(
        data, is_months=3, oos_months=2, step_months=2
    )
    assert len(windows) <= MAX_WFA_WINDOWS


def test_generate_walk_forward_windows_requires_datetime_index() -> None:
    data = _make_data(10).reset_index(drop=True)
    with pytest.raises(ValueError, match="DatetimeIndex"):
        generate_walk_forward_windows(data, is_months=3, oos_months=2, step_months=2)


# ---------------------------------------------------------------------------
# run_walk_forward_analysis — validation
# ---------------------------------------------------------------------------

def test_run_walk_forward_rejects_profit_factor_metric() -> None:
    data = _make_data(10)
    with pytest.raises(ValueError, match="profit_factor"):
        run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            optimize_metric="profit_factor",
            is_months=3, oos_months=2, step_months=2,
        )


def test_run_walk_forward_rejects_max_drawdown_metric() -> None:
    data = _make_data(10)
    with pytest.raises(ValueError, match="max_drawdown"):
        run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            optimize_metric="max_drawdown",
            is_months=3, oos_months=2, step_months=2,
        )


def test_walk_forward_excludes_dca() -> None:
    data = _make_data(10)
    with pytest.raises(ValueError, match="dollar_cost_averaging"):
        run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="dollar_cost_averaging",
            param_ranges={},
            optimize_metric="sharpe_ratio",
            is_months=3, oos_months=2, step_months=2,
        )


def test_walk_forward_respects_max_combos() -> None:
    # 15×15 = 225 valid combos > 200
    data = _make_data(5)  # data length doesn't matter; combo check happens first
    short_vals = list(range(1, 16))
    long_vals = list(range(16, 31))
    with pytest.raises(ValueError, match="超過上限"):
        run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": short_vals, "long_window": long_vals},
            optimize_metric="sharpe_ratio",
            is_months=3, oos_months=2, step_months=2,
        )


# ---------------------------------------------------------------------------
# run_walk_forward_analysis — with mocks
# ---------------------------------------------------------------------------

def _run_wfa_mocked(
    data: pd.DataFrame,
    sweep_results: list[SweepResult] | None = None,
    oos_result=None,
    strategy_type: str = "moving_average_cross",
    optimize_metric: str = "sharpe_ratio",
    is_months: int = 3,
    oos_months: int = 2,
    step_months: int = 2,
) -> WalkForwardSummary:
    """Helper: run WFA with sweep and engine mocked."""
    if sweep_results is None:
        run = _make_sweep_run({"short_window": 5.0, "long_window": 20.0}, sharpe_ratio=1.5)
        sweep_results = [_make_sweep_result([run])]

    if oos_result is None:
        oos_result = _make_oos_result()

    sweep_iter = iter(sweep_results)

    def _mock_sweep(**kwargs):
        try:
            return next(sweep_iter)
        except StopIteration:
            return sweep_results[-1]

    with (
        mock.patch("src.backtest.walk_forward.run_parameter_sweep", side_effect=_mock_sweep),
        mock.patch("src.backtest.walk_forward.VectorizedBacktester") as mock_engine_cls,
        mock.patch("src.backtest.walk_forward._build_strategy", return_value=mock.MagicMock()),
    ):
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = oos_result
        mock_engine_cls.return_value = mock_engine

        return run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type=strategy_type,
            param_ranges={"short_window": [5], "long_window": [20]},
            optimize_metric=optimize_metric,
            is_months=is_months,
            oos_months=oos_months,
            step_months=step_months,
        )


def test_run_walk_forward_returns_window_results() -> None:
    data = _make_data(10)
    summary = _run_wfa_mocked(data)
    assert isinstance(summary, WalkForwardSummary)
    assert summary.total_window_count >= MIN_WFA_WINDOWS
    assert len(summary.windows) == summary.total_window_count


def test_run_walk_forward_uses_is_for_sweep_and_oos_for_validation() -> None:
    data = _make_data(10)
    captured_is: list[pd.DataFrame] = []
    captured_oos: list[pd.DataFrame] = []

    run = _make_sweep_run({"short_window": 5.0, "long_window": 20.0})
    sweep_result = _make_sweep_result([run])

    def _capture_sweep(**kwargs):
        captured_is.append(kwargs["data"])
        return sweep_result

    with (
        mock.patch("src.backtest.walk_forward.run_parameter_sweep", side_effect=_capture_sweep),
        mock.patch("src.backtest.walk_forward.VectorizedBacktester") as mock_engine_cls,
        mock.patch("src.backtest.walk_forward._build_strategy", return_value=mock.MagicMock()),
    ):
        mock_engine = mock.MagicMock()

        def _capture_run(strategy, data):
            captured_oos.append(data)
            return _make_oos_result()

        mock_engine.run.side_effect = _capture_run
        mock_engine_cls.return_value = mock_engine

        summary = run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            is_months=3,
            oos_months=2,
            step_months=2,
        )

    assert len(captured_is) == summary.total_window_count
    assert len(captured_oos) == summary.valid_window_count

    # IS data must end before OOS data starts for each window
    for i, wr in enumerate(summary.windows):
        if not wr.skipped:
            assert captured_is[i].index.max() < wr.window.oos_start


def test_run_walk_forward_selects_best_params_by_metric() -> None:
    data = _make_data(10)
    # Two sweep runs: second has higher sharpe
    run_low = _make_sweep_run({"short_window": 5.0, "long_window": 20.0}, sharpe_ratio=0.5)
    run_high = _make_sweep_run({"short_window": 10.0, "long_window": 40.0}, sharpe_ratio=2.0)
    sweep_result = _make_sweep_result([run_low, run_high])

    summary = _run_wfa_mocked(
        data,
        sweep_results=[sweep_result] * 10,
        optimize_metric="sharpe_ratio",
    )

    for wr in summary.windows:
        if not wr.skipped and wr.best_params:
            assert wr.best_params == {"short_window": 10.0, "long_window": 40.0}


def test_run_walk_forward_records_degradation() -> None:
    data = _make_data(10)
    # IS best sharpe = 2.0, OOS sharpe = 1.2 → degradation = 1.2 - 2.0 = -0.8
    run = _make_sweep_run({"short_window": 5.0, "long_window": 20.0}, sharpe_ratio=2.0)
    sweep_result = _make_sweep_result([run])
    oos = _make_oos_result(sharpe_ratio=1.2)

    summary = _run_wfa_mocked(data, sweep_results=[sweep_result] * 10, oos_result=oos)

    for wr in summary.windows:
        if not wr.skipped:
            assert wr.degradation == pytest.approx(-0.8)


def test_run_walk_forward_sets_low_trade_warning() -> None:
    data = _make_data(10)
    oos = _make_oos_result(total_trades=MIN_OOS_TRADES_WARNING - 1)

    summary = _run_wfa_mocked(data, oos_result=oos)

    for wr in summary.windows:
        if not wr.skipped:
            assert any("交易樣本不足" in w for w in wr.warnings)


def test_run_walk_forward_skips_failed_sweep_window() -> None:
    data = _make_data(10)
    # All runs have errors → no best params → skipped
    failed_run = _make_sweep_run({"short_window": 5.0, "long_window": 20.0}, error="fail")
    sweep_result = _make_sweep_result([failed_run])

    with (
        mock.patch("src.backtest.walk_forward.run_parameter_sweep", return_value=sweep_result),
        mock.patch("src.backtest.walk_forward._build_strategy", return_value=mock.MagicMock()),
    ):
        summary = run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            is_months=3,
            oos_months=2,
            step_months=2,
        )

    assert summary.skipped_window_count == summary.total_window_count
    assert summary.valid_window_count == 0
    for wr in summary.windows:
        assert wr.skipped is True
        assert wr.best_params is None


def test_walk_forward_valid_window_count_excludes_skipped() -> None:
    data = _make_data(10)
    call_count = [0]

    def _alternating_sweep(**kwargs):
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            # even calls → failed sweep
            failed = _make_sweep_run({"short_window": 5.0, "long_window": 20.0}, error="fail")
            return _make_sweep_result([failed])
        run = _make_sweep_run({"short_window": 5.0, "long_window": 20.0})
        return _make_sweep_result([run])

    with (
        mock.patch("src.backtest.walk_forward.run_parameter_sweep", side_effect=_alternating_sweep),
        mock.patch("src.backtest.walk_forward.VectorizedBacktester") as mock_engine_cls,
        mock.patch("src.backtest.walk_forward._build_strategy", return_value=mock.MagicMock()),
    ):
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = _make_oos_result()
        mock_engine_cls.return_value = mock_engine

        summary = run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            is_months=3,
            oos_months=2,
            step_months=2,
        )

    assert summary.valid_window_count + summary.skipped_window_count == summary.total_window_count
    assert summary.valid_window_count < summary.total_window_count


def test_warning_count_includes_per_window_and_unstable_param() -> None:
    """warning_count must sum per-window warnings AND aggregate warnings (incl. unstable params)."""
    data = _make_data(10)

    # Each window: OOS trades < 3 → 1 per-window warning per valid window
    oos = _make_oos_result(total_trades=MIN_OOS_TRADES_WARNING - 1)

    # IS best sharpe varies across windows → unstable parameter
    call_count = [0]
    params_by_call = [
        {"short_window": 2.0, "long_window": 20.0},   # call 1
        {"short_window": 18.0, "long_window": 40.0},  # call 2 — CV will be high
        {"short_window": 2.0, "long_window": 20.0},   # call 3
    ]

    def _varying_sweep(**kwargs):
        idx = call_count[0] % len(params_by_call)
        call_count[0] += 1
        params = params_by_call[idx]
        run = _make_sweep_run(params, sharpe_ratio=1.5)
        return _make_sweep_result([run])

    with (
        mock.patch("src.backtest.walk_forward.run_parameter_sweep", side_effect=_varying_sweep),
        mock.patch("src.backtest.walk_forward.VectorizedBacktester") as mock_engine_cls,
        mock.patch("src.backtest.walk_forward._build_strategy", return_value=mock.MagicMock()),
    ):
        mock_engine = mock.MagicMock()
        mock_engine.run.return_value = oos
        mock_engine_cls.return_value = mock_engine

        summary = run_walk_forward_analysis(
            symbol="2330",
            data=data,
            strategy_type="moving_average_cross",
            param_ranges={"short_window": [5], "long_window": [20]},
            is_months=3,
            oos_months=2,
            step_months=2,
        )

    per_window_warnings = sum(len(wr.warnings) for wr in summary.windows)
    agg_warnings = len(summary.aggregate["warnings"])
    expected = per_window_warnings + agg_warnings
    assert summary.aggregate["warning_count"] == expected
    assert per_window_warnings > 0  # sanity: low-trade warnings exist


# ---------------------------------------------------------------------------
# calculate_parameter_stability
# ---------------------------------------------------------------------------

def test_parameter_stability_stable() -> None:
    # CV = std / mean; all same value → std=0, cv=0 → stable
    results = [_make_wf_result({"short_window": 10.0}) for _ in range(4)]
    stability = calculate_parameter_stability(results)
    assert stability["overall_status"] == "stable"
    assert stability["params"]["short_window"]["status"] == "stable"
    assert stability["params"]["short_window"]["cv"] == pytest.approx(0.0)


def test_parameter_stability_moderate() -> None:
    # cv in [0.15, 0.40)
    # mean=10, values=[8,12] → std=2, cv=0.2 → moderate
    results = [
        _make_wf_result({"p": 8.0}),
        _make_wf_result({"p": 12.0}),
    ]
    stability = calculate_parameter_stability(results)
    assert stability["params"]["p"]["status"] == "moderate"


def test_parameter_stability_unstable() -> None:
    # cv >= 0.40 → unstable
    # mean=10, values=[2,18] → std=8, cv=0.8
    results = [
        _make_wf_result({"p": 2.0}),
        _make_wf_result({"p": 18.0}),
    ]
    stability = calculate_parameter_stability(results)
    assert stability["params"]["p"]["status"] == "unstable"
    assert stability["overall_status"] == "unstable"


def test_parameter_stability_skipped_excluded() -> None:
    # skipped windows ignored
    results = [
        _make_wf_result({"p": 10.0}),
        _make_wf_result(None, skipped=True),  # should not affect
    ]
    stability = calculate_parameter_stability(results)
    assert "p" in stability["params"]
    assert stability["params"]["p"]["mean"] == pytest.approx(10.0)


def test_parameter_stability_no_valid_windows() -> None:
    results = [_make_wf_result(None, skipped=True) for _ in range(3)]
    stability = calculate_parameter_stability(results)
    assert stability["overall_status"] == "unstable"
    assert stability["params"] == {}


def test_parameter_stability_mean_zero_is_unstable() -> None:
    # mean=0 → CV undefined → unstable
    results = [
        _make_wf_result({"p": 0.0}),
        _make_wf_result({"p": 0.0}),
    ]
    stability = calculate_parameter_stability(results)
    assert stability["params"]["p"]["status"] == "unstable"


def test_parameter_stability_stat_fields() -> None:
    results = [
        _make_wf_result({"short_window": 5.0}),
        _make_wf_result({"short_window": 10.0}),
        _make_wf_result({"short_window": 15.0}),
    ]
    stability = calculate_parameter_stability(results)
    stat = stability["params"]["short_window"]
    assert stat["min"] == pytest.approx(5.0)
    assert stat["max"] == pytest.approx(15.0)
    assert stat["mean"] == pytest.approx(10.0)
    assert stat["median"] == pytest.approx(10.0)
    assert "std" in stat
    assert "cv" in stat
    assert "status" in stat


# ---------------------------------------------------------------------------
# save_walk_forward_summary_csv
# ---------------------------------------------------------------------------

def _make_summary(n_windows: int = 2) -> WalkForwardSummary:
    def _oos():
        r = mock.MagicMock()
        r.total_return = 0.05
        r.annual_return = 0.03
        r.max_drawdown = 0.08
        r.sharpe_ratio = 1.2
        r.total_trades = 10
        return r

    def _is_best():
        r = mock.MagicMock()
        r.total_return = 0.08
        r.annual_return = 0.05
        r.sharpe_ratio = 1.5
        return r

    windows = []
    for i in range(n_windows):
        win = WalkForwardWindow(
            window_id=i,
            is_start=pd.Timestamp("2020-01-01", tz="Asia/Taipei"),
            is_end=pd.Timestamp("2020-03-31", tz="Asia/Taipei"),
            oos_start=pd.Timestamp("2020-04-01", tz="Asia/Taipei"),
            oos_end=pd.Timestamp("2020-05-31", tz="Asia/Taipei"),
        )
        windows.append(WalkForwardWindowResult(
            window=win,
            best_params={"short_window": 5.0, "long_window": 20.0},
            is_best=_is_best(),
            oos_result=_oos(),
            degradation=-0.3,
            skipped=False,
        ))

    return WalkForwardSummary(
        strategy_type="moving_average_cross",
        optimize_metric="sharpe_ratio",
        windows=windows,
        total_window_count=n_windows,
        valid_window_count=n_windows,
        skipped_window_count=0,
        aggregate={
            "oos_win_window_rate": 1.0,
            "avg_oos_return": 0.05,
            "median_oos_return": 0.05,
            "avg_oos_sharpe": 1.2,
            "worst_oos_drawdown": 0.08,
            "avg_degradation": -0.3,
            "warning_count": 0,
            "warnings": [],
        },
        parameter_stability={
            "overall_status": "stable",
            "params": {
                "short_window": {
                    "min": 5.0, "max": 5.0, "mean": 5.0,
                    "median": 5.0, "std": 0.0, "cv": 0.0, "status": "stable",
                }
            },
        },
    )


def test_save_walk_forward_csv_creates_files(tmp_path: Path) -> None:
    summary = _make_summary()
    win_path, stab_path = save_walk_forward_summary_csv(summary, output_dir=tmp_path)

    assert win_path.exists()
    assert stab_path.exists()


def test_save_walk_forward_csv_window_columns(tmp_path: Path) -> None:
    summary = _make_summary()
    win_path, _ = save_walk_forward_summary_csv(summary, output_dir=tmp_path)

    df = pd.read_csv(win_path, encoding="utf-8-sig")
    for col in ("window_id", "is_start", "is_end", "oos_start", "oos_end",
                "best_params", "is_total_return", "is_sharpe",
                "oos_total_return", "oos_sharpe", "oos_max_drawdown",
                "oos_total_trades", "degradation", "skipped", "warnings"):
        assert col in df.columns, f"missing column: {col}"
    assert len(df) == 2


def test_save_walk_forward_csv_stability_columns(tmp_path: Path) -> None:
    summary = _make_summary()
    _, stab_path = save_walk_forward_summary_csv(summary, output_dir=tmp_path)

    df = pd.read_csv(stab_path, encoding="utf-8-sig")
    for col in ("param", "min", "max", "mean", "median", "std", "cv", "status"):
        assert col in df.columns, f"missing column: {col}"
    assert len(df) == 1
    assert df.loc[0, "param"] == "short_window"


def test_save_walk_forward_csv_filename_format(tmp_path: Path) -> None:
    summary = _make_summary()
    win_path, stab_path = save_walk_forward_summary_csv(summary, output_dir=tmp_path)

    assert "moving_average_cross" in win_path.name
    assert "wfa_windows" in win_path.name
    assert "moving_average_cross" in stab_path.name
    assert "wfa_stability" in stab_path.name


def test_save_walk_forward_csv_skipped_window(tmp_path: Path) -> None:
    summary = _make_summary(n_windows=0)
    # Add a skipped window manually
    win = WalkForwardWindow(
        window_id=0,
        is_start=pd.Timestamp("2020-01-01", tz="Asia/Taipei"),
        is_end=pd.Timestamp("2020-03-31", tz="Asia/Taipei"),
        oos_start=pd.Timestamp("2020-04-01", tz="Asia/Taipei"),
        oos_end=pd.Timestamp("2020-05-31", tz="Asia/Taipei"),
    )
    skipped = WalkForwardWindowResult(
        window=win,
        best_params=None,
        is_best=None,
        oos_result=None,
        degradation=None,
        skipped=True,
        warnings=["IS 掃描全部失敗，跳過此視窗"],
    )
    summary_with_skip = WalkForwardSummary(
        strategy_type="rsi",
        optimize_metric="sharpe_ratio",
        windows=[skipped],
        total_window_count=1,
        valid_window_count=0,
        skipped_window_count=1,
        aggregate={"oos_win_window_rate": 0.0, "avg_oos_return": 0.0,
                   "median_oos_return": 0.0, "avg_oos_sharpe": 0.0,
                   "worst_oos_drawdown": 0.0, "avg_degradation": None,
                   "warning_count": 1, "warnings": ["視窗數過少，WFA 可信度有限"]},
        parameter_stability={"overall_status": "unstable", "params": {}},
    )
    win_path, stab_path = save_walk_forward_summary_csv(summary_with_skip, output_dir=tmp_path)

    df = pd.read_csv(win_path, encoding="utf-8-sig")
    assert df.loc[0, "skipped"] == True  # noqa: E712
    assert "掃描全部失敗" in df.loc[0, "warnings"]

    stab_df = pd.read_csv(stab_path, encoding="utf-8-sig")
    assert len(stab_df) == 0
    for col in ("param", "min", "max", "mean", "median", "std", "cv", "status"):
        assert col in stab_df.columns
