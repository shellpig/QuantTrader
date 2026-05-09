"""Parameter sweep (Grid Search) for Phase 7-C."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from itertools import product
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest.batch import _build_strategy
from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.metrics import BacktestResult
from src.core.strategy_config import (
    _normalize_bias_params,
    _normalize_bollinger_band_params,
    _normalize_donchian_breakout_params,
    _normalize_kd_cross_params,
    _normalize_macd_cross_params,
    _normalize_moving_average_params,
    _normalize_rsi_params,
)

MAX_COMBOS = 200
MAX_SWEEP_COMBOS = MAX_COMBOS

# Sweepable strategies (DCA excluded) and their parameter keys in order.
SWEEP_PARAM_SPECS: dict[str, list[str]] = {
    "moving_average_cross": ["short_window", "long_window"],
    "rsi": ["period", "oversold", "overbought"],
    "kd_cross": ["k_period", "d_period", "smooth_k"],
    "macd_cross": ["fast", "slow", "signal"],
    "bollinger_band": ["period", "std_dev"],
    "bias": ["ma_period", "buy_bias", "sell_bias"],
    "donchian_breakout": ["entry_period", "exit_period"],
}

_NORMALIZERS = {
    "moving_average_cross": _normalize_moving_average_params,
    "rsi": _normalize_rsi_params,
    "kd_cross": _normalize_kd_cross_params,
    "macd_cross": _normalize_macd_cross_params,
    "bollinger_band": _normalize_bollinger_band_params,
    "bias": _normalize_bias_params,
    "donchian_breakout": _normalize_donchian_breakout_params,
}


@dataclass
class SweepRunSummary:
    params: dict[str, Any]
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    error: str | None
    sample_warning: bool = False
    result: BacktestResult | None = field(default=None, repr=False)


@dataclass
class SweepResult:
    symbol: str
    start_date: str
    end_date: str
    strategy_type: str
    total_combos: int
    valid_combos: int
    results: list[SweepRunSummary]


def parse_param_values(raw: str) -> list[float]:
    """Parse comma-separated string to sorted, deduplicated list of floats.

    Returns empty list on parse error or empty input.
    """
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        return []
    try:
        values = [float(p) for p in parts]
    except ValueError:
        return []
    return sorted(set(values))


def generate_param_grid(
    strategy_type: str,
    param_candidates: dict[str, list[Any]],
) -> tuple[int, list[dict[str, Any]]]:
    """Cartesian product of param_candidates filtered by strategy's normalizer.

    Returns (total_combos_before_filter, valid_combos_list).
    """
    param_keys = list(param_candidates.keys())
    param_values = [param_candidates[k] for k in param_keys]

    all_combos = [dict(zip(param_keys, combo)) for combo in product(*param_values)]
    total_combos = len(all_combos)

    normalizer = _NORMALIZERS.get(strategy_type)
    if normalizer is None:
        return total_combos, all_combos

    valid = [c for c in all_combos if normalizer(c) is not None]
    return total_combos, valid


def run_parameter_sweep(
    *,
    data: pd.DataFrame,
    symbol: str,
    start_date: str,
    end_date: str,
    strategy_type: str,
    param_candidates: dict[str, list[Any]],
    initial_capital: float = 1_000_000,
) -> SweepResult:
    """Run VectorizedBacktester for every valid parameter combination.

    Raises ValueError if valid combo count exceeds MAX_COMBOS.
    """
    total_combos, valid_list = generate_param_grid(strategy_type, param_candidates)

    if len(valid_list) > MAX_COMBOS:
        raise ValueError(
            f"合法組合數 {len(valid_list)} 超過上限 {MAX_COMBOS}，請縮小參數範圍。"
        )

    results: list[SweepRunSummary] = []
    for params in valid_list:
        try:
            strategy = _build_strategy(strategy_type, params)
            engine = VectorizedBacktester(initial_capital=initial_capital)
            bt = engine.run(strategy=strategy, data=data)
            results.append(SweepRunSummary(
                params=params,
                total_return=bt.total_return,
                annual_return=bt.annual_return,
                max_drawdown=bt.max_drawdown,
                sharpe_ratio=bt.sharpe_ratio,
                win_rate=bt.win_rate,
                profit_factor=bt.profit_factor,
                total_trades=bt.total_trades,
                error=None,
                sample_warning=bt.total_trades < 3,
                result=bt,
            ))
        except Exception as exc:  # noqa: BLE001
            results.append(SweepRunSummary(
                params=params,
                total_return=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                error=str(exc),
                sample_warning=False,
                result=None,
            ))

    return SweepResult(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        strategy_type=strategy_type,
        total_combos=total_combos,
        valid_combos=len(valid_list),
        results=results,
    )


def save_sweep_result_csv(sweep: SweepResult) -> Path:
    """Save sweep results to CSV; returns the saved file path."""
    out_dir = Path("data/backtest/parameter_sweeps")
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"{sweep.symbol}_{sweep.strategy_type}_{ts}.csv"
    filepath = out_dir / filename

    rows = []
    for s in sweep.results:
        pf = s.profit_factor
        row: dict[str, Any] = dict(s.params)
        row.update({
            "總報酬": f"{s.total_return * 100:.2f}%" if not s.error else "—",
            "年化報酬": f"{s.annual_return * 100:.2f}%" if not s.error else "—",
            "最大回撤": f"{s.max_drawdown * 100:.2f}%" if not s.error else "—",
            "Sharpe": f"{s.sharpe_ratio:.2f}" if not s.error else "—",
            "勝率": f"{s.win_rate * 100:.2f}%" if not s.error else "—",
            "Profit Factor": ("N/A" if pf >= 999.0 else f"{pf:.2f}") if not s.error else "—",
            "交易次數": s.total_trades if not s.error else "—",
            "sample_warning": s.sample_warning,
            "錯誤": s.error or "",
        })
        rows.append(row)

    pd.DataFrame(rows).to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath
