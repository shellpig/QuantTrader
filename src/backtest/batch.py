"""Batch strategy comparison for backtesting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.metrics import BacktestResult


@dataclass
class StrategyRunSummary:
    preset_name: str
    strategy_type: str
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    error: str | None
    result: BacktestResult | None


@dataclass
class BatchResult:
    symbol: str
    start_date: str
    end_date: str
    engine: str
    initial_capital: float
    summaries: list[StrategyRunSummary]


def run_strategy_batch(
    *,
    data: pd.DataFrame,
    symbol: str,
    start_date: str,
    end_date: str,
    presets: list[dict[str, Any]],
    initial_capital: float = 1_000_000,
) -> BatchResult:
    """Run VectorizedBacktester for each preset; collect StrategyRunSummary per preset."""
    summaries: list[StrategyRunSummary] = []

    for preset in presets:
        preset_name = str(preset.get("name", ""))
        strategy_type = str(preset.get("type", "")).strip().lower()
        params: dict[str, Any] = preset.get("params", {}) if isinstance(preset.get("params"), dict) else {}

        if strategy_type == "dollar_cost_averaging":
            summaries.append(StrategyRunSummary(
                preset_name=preset_name,
                strategy_type=strategy_type,
                total_return=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                error="定期定額策略不支援批次比較，請至單次回測頁執行",
                result=None,
            ))
            continue

        try:
            strategy = _build_strategy(strategy_type, params)
            engine = VectorizedBacktester(initial_capital=initial_capital)
            result = engine.run(strategy=strategy, data=data)
            summaries.append(StrategyRunSummary(
                preset_name=preset_name,
                strategy_type=strategy_type,
                total_return=result.total_return,
                annual_return=result.annual_return,
                max_drawdown=result.max_drawdown,
                sharpe_ratio=result.sharpe_ratio,
                win_rate=result.win_rate,
                profit_factor=result.profit_factor,
                total_trades=result.total_trades,
                error=None,
                result=result,
            ))
        except Exception as exc:  # noqa: BLE001
            summaries.append(StrategyRunSummary(
                preset_name=preset_name,
                strategy_type=strategy_type,
                total_return=0.0,
                annual_return=0.0,
                max_drawdown=0.0,
                sharpe_ratio=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                error=str(exc),
                result=None,
            ))

    return BatchResult(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        engine="vectorized",
        initial_capital=initial_capital,
        summaries=summaries,
    )


def save_batch_result_csv(batch_result: BatchResult) -> Path:
    """Save batch result summaries to CSV. Returns the saved file path."""
    out_dir = Path("data/backtest/strategy_comparisons")
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%dT%H%M%S")
    start_clean = batch_result.start_date.replace("-", "")
    end_clean = batch_result.end_date.replace("-", "")
    filename = f"{batch_result.symbol}_{start_clean}_{end_clean}_{ts}.csv"
    filepath = out_dir / filename

    rows = []
    for s in batch_result.summaries:
        pf = s.profit_factor
        rows.append({
            "策略名稱": s.preset_name,
            "策略類型": s.strategy_type,
            "總報酬": f"{s.total_return * 100:.2f}%",
            "年化報酬": f"{s.annual_return * 100:.2f}%",
            "最大回撤": f"{s.max_drawdown * 100:.2f}%",
            "Sharpe": f"{s.sharpe_ratio:.2f}",
            "勝率": f"{s.win_rate * 100:.2f}%",
            "Profit Factor": "N/A" if pf >= 999.0 else f"{pf:.2f}",
            "交易次數": s.total_trades,
            "錯誤": s.error or "",
        })

    pd.DataFrame(rows).to_csv(filepath, index=False, encoding="utf-8-sig")
    return filepath


def _build_strategy(strategy_type: str, params: dict[str, Any]):
    """Instantiate a strategy from type string and params dict."""
    from src.strategy.examples.bias import BiasStrategy
    from src.strategy.examples.bollinger_band import BollingerBandStrategy
    from src.strategy.examples.donchian_breakout import DonchianBreakoutStrategy
    from src.strategy.examples.kd_cross import KDCrossStrategy
    from src.strategy.examples.ma_cross import MACrossStrategy
    from src.strategy.examples.macd_cross import MACDCrossStrategy
    from src.strategy.examples.rsi import RSIStrategy

    if strategy_type == "moving_average_cross":
        return MACrossStrategy(
            ma_short=int(params.get("short_window", 20)),
            ma_long=int(params.get("long_window", 60)),
        )
    if strategy_type == "rsi":
        return RSIStrategy(
            period=int(params.get("period", 14)),
            oversold=float(params.get("oversold", 30)),
            overbought=float(params.get("overbought", 70)),
        )
    if strategy_type == "kd_cross":
        return KDCrossStrategy(
            k_period=int(params.get("k_period", 9)),
            d_period=int(params.get("d_period", 3)),
            smooth_k=int(params.get("smooth_k", 3)),
        )
    if strategy_type == "macd_cross":
        return MACDCrossStrategy(
            fast=int(params.get("fast", 12)),
            slow=int(params.get("slow", 26)),
            signal=int(params.get("signal", 9)),
        )
    if strategy_type == "bollinger_band":
        return BollingerBandStrategy(
            period=int(params.get("period", 20)),
            std_dev=float(params.get("std_dev", 2.0)),
        )
    if strategy_type == "bias":
        return BiasStrategy(
            ma_period=int(params.get("ma_period", 20)),
            buy_bias=float(params.get("buy_bias", -10.0)),
            sell_bias=float(params.get("sell_bias", 10.0)),
        )
    if strategy_type == "donchian_breakout":
        return DonchianBreakoutStrategy(
            entry_period=int(params.get("entry_period", 20)),
            exit_period=int(params.get("exit_period", 10)),
        )
    raise ValueError(f"不支援的策略類型：{strategy_type}")
