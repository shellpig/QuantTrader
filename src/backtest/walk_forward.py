"""Walk-Forward Analysis (WFA) for Phase 7-D."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest.batch import _build_strategy
from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.metrics import BacktestResult
from src.backtest.sweep import (
    MAX_COMBOS,
    SWEEP_PARAM_SPECS,
    SweepRunSummary,
    generate_param_grid,
    run_parameter_sweep,
)

DEFAULT_IS_MONTHS = 12
DEFAULT_OOS_MONTHS = 6
DEFAULT_STEP_MONTHS = 6
MIN_WFA_WINDOWS = 3
MAX_WFA_WINDOWS = 10
MIN_OOS_TRADES_WARNING = 3
SUPPORTED_OPTIMIZE_METRICS: frozenset[str] = frozenset(
    {"total_return", "annual_return", "sharpe_ratio"}
)


@dataclass(frozen=True)
class WalkForwardWindow:
    window_id: int
    is_start: pd.Timestamp
    is_end: pd.Timestamp
    oos_start: pd.Timestamp
    oos_end: pd.Timestamp


@dataclass(frozen=True)
class WalkForwardWindowResult:
    window: WalkForwardWindow
    best_params: dict[str, Any] | None
    is_best: SweepRunSummary | None
    oos_result: BacktestResult | None
    degradation: float | None
    skipped: bool
    warnings: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WalkForwardSummary:
    strategy_type: str
    optimize_metric: str
    windows: list[WalkForwardWindowResult]
    total_window_count: int
    valid_window_count: int
    skipped_window_count: int
    aggregate: dict[str, Any]
    parameter_stability: dict[str, Any]


def required_months_for_wfa(
    *,
    is_months: int,
    oos_months: int,
    step_months: int,
    min_windows: int = MIN_WFA_WINDOWS,
) -> int:
    return is_months + oos_months + (min_windows - 1) * step_months


def generate_walk_forward_windows(
    data: pd.DataFrame,
    *,
    is_months: int = DEFAULT_IS_MONTHS,
    oos_months: int = DEFAULT_OOS_MONTHS,
    step_months: int = DEFAULT_STEP_MONTHS,
    min_windows: int = MIN_WFA_WINDOWS,
    max_windows: int = MAX_WFA_WINDOWS,
) -> list[WalkForwardWindow]:
    """Generate rolling IS/OOS windows using calendar months.

    Raises ValueError if data has no DatetimeIndex or is too short.
    """
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("data index 必須是 DatetimeIndex")
    if is_months <= 0 or oos_months <= 0 or step_months <= 0:
        raise ValueError("is_months, oos_months, step_months 必須 > 0")
    max_windows = min(max_windows, MAX_WFA_WINDOWS)

    data_start = data.index.min()
    data_end = data.index.max()

    windows: list[WalkForwardWindow] = []
    is_offset = data_start

    while len(windows) < max_windows:
        is_end_excl = is_offset + pd.DateOffset(months=is_months)
        oos_end_excl = is_end_excl + pd.DateOffset(months=oos_months)

        if oos_end_excl > data_end + pd.Timedelta(days=1):
            break

        is_data = data[(data.index >= is_offset) & (data.index < is_end_excl)]
        oos_data = data[(data.index >= is_end_excl) & (data.index < oos_end_excl)]

        if len(is_data) == 0 or len(oos_data) == 0:
            break

        windows.append(
            WalkForwardWindow(
                window_id=len(windows),
                is_start=is_data.index.min(),
                is_end=is_data.index.max(),
                oos_start=oos_data.index.min(),
                oos_end=oos_data.index.max(),
            )
        )
        is_offset = is_offset + pd.DateOffset(months=step_months)

    if len(windows) < min_windows:
        required = required_months_for_wfa(
            is_months=is_months,
            oos_months=oos_months,
            step_months=step_months,
            min_windows=min_windows,
        )
        actual = (
            (data_end.year - data_start.year) * 12
            + (data_end.month - data_start.month)
        )
        raise ValueError(
            f"資料長度不足：目前資料僅 {actual} 個月，WFA 至少需要 {required} 個月"
            f"（IS {is_months} + OOS {oos_months} + {min_windows - 1} 段步進 × {step_months}）。"
        )

    return windows


def _select_best_sweep_run(
    sweep_runs: list[SweepRunSummary],
    optimize_metric: str,
) -> SweepRunSummary | None:
    candidates = [r for r in sweep_runs if r.error is None and r.result is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda r: getattr(r, optimize_metric))


def _calculate_degradation(
    is_best: SweepRunSummary,
    oos_result: BacktestResult,
    optimize_metric: str,
) -> float:
    return getattr(oos_result, optimize_metric) - getattr(is_best, optimize_metric)


def calculate_parameter_stability(
    window_results: list[WalkForwardWindowResult],
) -> dict[str, Any]:
    """Compute CV-based stability for each numeric param across valid windows."""
    valid = [
        wr for wr in window_results
        if not wr.skipped and wr.best_params is not None
    ]
    if not valid:
        return {"overall_status": "unstable", "params": {}}

    param_names: set[str] = set()
    for wr in valid:
        for k, v in wr.best_params.items():
            if isinstance(v, (int, float)):
                param_names.add(k)

    params_stats: dict[str, Any] = {}
    for param in sorted(param_names):
        values = [
            float(wr.best_params[param])
            for wr in valid
            if param in wr.best_params and isinstance(wr.best_params[param], (int, float))
        ]
        if not values:
            continue

        mean = statistics.mean(values)
        std = statistics.pstdev(values)

        if mean == 0:
            cv = float("inf")
            status = "unstable"
        else:
            cv = std / abs(mean)
            if cv < 0.15:
                status = "stable"
            elif cv < 0.40:
                status = "moderate"
            else:
                status = "unstable"

        params_stats[param] = {
            "min": min(values),
            "max": max(values),
            "mean": mean,
            "median": statistics.median(values),
            "std": std,
            "cv": cv,
            "status": status,
        }

    if not params_stats:
        overall = "unstable"
    else:
        statuses = [p["status"] for p in params_stats.values()]
        if "unstable" in statuses:
            overall = "unstable"
        elif "moderate" in statuses:
            overall = "moderate"
        else:
            overall = "stable"

    return {"overall_status": overall, "params": params_stats}


def _build_walk_forward_aggregate(
    window_results: list[WalkForwardWindowResult],
) -> dict[str, Any]:
    """Aggregate OOS metrics from non-skipped valid windows."""
    valid = [
        wr for wr in window_results
        if not wr.skipped and wr.oos_result is not None
    ]

    agg_warnings: list[str] = []
    if len(valid) < MIN_WFA_WINDOWS:
        agg_warnings.append("視窗數過少，WFA 可信度有限")

    if not valid:
        return {
            "oos_win_window_rate": 0.0,
            "avg_oos_return": 0.0,
            "median_oos_return": 0.0,
            "avg_oos_sharpe": 0.0,
            "worst_oos_drawdown": 0.0,
            "avg_degradation": None,
            "warning_count": len(agg_warnings),
            "warnings": agg_warnings,
        }

    oos_returns = [wr.oos_result.total_return for wr in valid]
    oos_sharpes = [wr.oos_result.sharpe_ratio for wr in valid]
    oos_drawdowns = [wr.oos_result.max_drawdown for wr in valid]
    degradations = [wr.degradation for wr in valid if wr.degradation is not None]

    win_rate = sum(1 for r in oos_returns if r > 0) / len(valid)
    avg_return = statistics.mean(oos_returns)
    avg_sharpe = statistics.mean(oos_sharpes)
    worst_drawdown = max(oos_drawdowns)
    avg_degradation = statistics.mean(degradations) if degradations else None

    if win_rate < 0.5:
        agg_warnings.append("策略泛化能力不足：大多數 OOS 視窗報酬為負")
    if avg_degradation is not None and avg_degradation < -0.05:
        agg_warnings.append("IS 績效無法延續到 OOS：平均 degradation 大幅為負")

    per_window_warning_count = sum(len(wr.warnings) for wr in window_results)

    return {
        "oos_win_window_rate": win_rate,
        "avg_oos_return": avg_return,
        "median_oos_return": statistics.median(oos_returns),
        "avg_oos_sharpe": avg_sharpe,
        "worst_oos_drawdown": worst_drawdown,
        "avg_degradation": avg_degradation,
        "warning_count": per_window_warning_count + len(agg_warnings),
        "warnings": agg_warnings,
    }


def run_walk_forward_analysis(
    *,
    symbol: str,
    data: pd.DataFrame,
    strategy_type: str,
    param_ranges: dict[str, list],
    optimize_metric: str = "sharpe_ratio",
    initial_capital: float = 1_000_000,
    is_months: int = DEFAULT_IS_MONTHS,
    oos_months: int = DEFAULT_OOS_MONTHS,
    step_months: int = DEFAULT_STEP_MONTHS,
    max_combinations: int = MAX_COMBOS,
) -> WalkForwardSummary:
    """Run rolling WFA: IS sweep → select best params → OOS validation."""
    if optimize_metric not in SUPPORTED_OPTIMIZE_METRICS:
        raise ValueError(
            f"optimize_metric '{optimize_metric}' 不支援；"
            f"請使用 {sorted(SUPPORTED_OPTIMIZE_METRICS)} 之一。"
        )
    if strategy_type not in SWEEP_PARAM_SPECS:
        raise ValueError(
            f"策略 '{strategy_type}' 不支援 Walk-Forward Analysis。"
        )

    _, valid_combos = generate_param_grid(strategy_type, param_ranges)
    if len(valid_combos) > max_combinations:
        raise ValueError(
            f"合法組合數 {len(valid_combos)} 超過上限 {max_combinations}，請縮小參數範圍。"
        )

    windows = generate_walk_forward_windows(
        data,
        is_months=is_months,
        oos_months=oos_months,
        step_months=step_months,
    )

    window_results: list[WalkForwardWindowResult] = []

    for win in windows:
        is_data = data[(data.index >= win.is_start) & (data.index <= win.is_end)]
        oos_data = data[(data.index >= win.oos_start) & (data.index <= win.oos_end)]

        sweep = run_parameter_sweep(
            data=is_data,
            symbol=symbol,
            start_date=str(win.is_start.date()),
            end_date=str(win.is_end.date()),
            strategy_type=strategy_type,
            param_candidates=param_ranges,
            initial_capital=initial_capital,
        )
        is_best = _select_best_sweep_run(sweep.results, optimize_metric)

        if is_best is None:
            window_results.append(
                WalkForwardWindowResult(
                    window=win,
                    best_params=None,
                    is_best=None,
                    oos_result=None,
                    degradation=None,
                    skipped=True,
                    warnings=["IS 掃描全部失敗，跳過此視窗"],
                )
            )
            continue

        oos_warnings: list[str] = []
        try:
            strategy = _build_strategy(strategy_type, is_best.params)
            engine = VectorizedBacktester(initial_capital=initial_capital)
            oos_result = engine.run(strategy=strategy, data=oos_data)
        except Exception as exc:  # noqa: BLE001
            window_results.append(
                WalkForwardWindowResult(
                    window=win,
                    best_params=is_best.params,
                    is_best=is_best,
                    oos_result=None,
                    degradation=None,
                    skipped=True,
                    warnings=[f"OOS 回測失敗：{exc}"],
                )
            )
            continue

        if oos_result.total_trades < MIN_OOS_TRADES_WARNING:
            oos_warnings.append(
                f"OOS 交易樣本不足（{oos_result.total_trades} 筆，"
                f"建議至少 {MIN_OOS_TRADES_WARNING} 筆）"
            )

        degradation = _calculate_degradation(is_best, oos_result, optimize_metric)

        window_results.append(
            WalkForwardWindowResult(
                window=win,
                best_params=is_best.params,
                is_best=is_best,
                oos_result=oos_result,
                degradation=degradation,
                skipped=False,
                warnings=oos_warnings,
            )
        )

    valid_count = sum(1 for wr in window_results if not wr.skipped)
    skipped_count = sum(1 for wr in window_results if wr.skipped)

    aggregate = _build_walk_forward_aggregate(window_results)
    stability = calculate_parameter_stability(window_results)

    # Propagate unstable-parameter warnings into aggregate
    if stability.get("overall_status") == "unstable":
        warnings_before = len(aggregate["warnings"])
        for param, stat in stability.get("params", {}).items():
            if stat["status"] == "unstable":
                msg = (
                    f"最佳參數在 WFA 視窗間變動過大（{param} CV={stat['cv']:.2f}），"
                    "可能代表策略對參數高度敏感。"
                )
                if msg not in aggregate["warnings"]:
                    aggregate["warnings"].append(msg)
        aggregate["warning_count"] += len(aggregate["warnings"]) - warnings_before

    return WalkForwardSummary(
        strategy_type=strategy_type,
        optimize_metric=optimize_metric,
        windows=window_results,
        total_window_count=len(window_results),
        valid_window_count=valid_count,
        skipped_window_count=skipped_count,
        aggregate=aggregate,
        parameter_stability=stability,
    )


def save_walk_forward_summary_csv(
    summary: WalkForwardSummary,
    output_dir: Path | str = Path("data/backtest/walk_forward"),
) -> tuple[Path, Path]:
    """Save WFA window summary and parameter stability as CSV files.

    Returns (window_csv_path, stability_csv_path).
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    window_path = out_dir / f"{summary.strategy_type}_wfa_windows_{ts}.csv"
    stability_path = out_dir / f"{summary.strategy_type}_wfa_stability_{ts}.csv"

    rows: list[dict[str, Any]] = []
    for wr in summary.windows:
        win = wr.window
        rows.append({
            "window_id": win.window_id,
            "is_start": str(win.is_start.date()),
            "is_end": str(win.is_end.date()),
            "oos_start": str(win.oos_start.date()),
            "oos_end": str(win.oos_end.date()),
            "best_params": str(wr.best_params) if wr.best_params else "",
            "is_total_return": f"{wr.is_best.total_return * 100:.2f}%" if wr.is_best else "",
            "is_sharpe": f"{wr.is_best.sharpe_ratio:.2f}" if wr.is_best else "",
            "oos_total_return": f"{wr.oos_result.total_return * 100:.2f}%" if wr.oos_result else "",
            "oos_sharpe": f"{wr.oos_result.sharpe_ratio:.2f}" if wr.oos_result else "",
            "oos_max_drawdown": f"{wr.oos_result.max_drawdown * 100:.2f}%" if wr.oos_result else "",
            "oos_total_trades": wr.oos_result.total_trades if wr.oos_result else "",
            "degradation": f"{wr.degradation:.4f}" if wr.degradation is not None else "",
            "skipped": wr.skipped,
            "warnings": "; ".join(wr.warnings),
        })
    pd.DataFrame(rows).to_csv(window_path, index=False, encoding="utf-8-sig")

    stab_rows: list[dict[str, Any]] = []
    for param, stat in summary.parameter_stability.get("params", {}).items():
        stab_rows.append({
            "param": param,
            "min": stat["min"],
            "max": stat["max"],
            "mean": stat["mean"],
            "median": stat["median"],
            "std": stat["std"],
            "cv": stat["cv"],
            "status": stat["status"],
        })
    stab_columns = ["param", "min", "max", "mean", "median", "std", "cv", "status"]
    pd.DataFrame(stab_rows, columns=stab_columns).to_csv(stability_path, index=False, encoding="utf-8-sig")

    return window_path, stability_path
