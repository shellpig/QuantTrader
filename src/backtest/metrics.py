"""Performance metrics for vectorized backtests."""

from __future__ import annotations

from dataclasses import dataclass
import math

import pandas as pd


@dataclass
class BacktestResult:
    """Backtest result container used by reporting layer."""

    equity_curve: pd.Series
    returns: pd.Series
    trades: pd.DataFrame
    total_return: float
    annual_return: float
    max_drawdown: float
    max_drawdown_start: str
    max_drawdown_end: str
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_holding_days: float
    max_single_loss: float
    signals: pd.Series | None = None


def calculate_metrics(
    equity_curve: pd.Series,
    trades: pd.DataFrame,
    risk_free_rate: float = 0.01,
    trading_days: int = 252,
    signals: pd.Series | None = None,
) -> BacktestResult:
    """Calculate common performance metrics from equity curve and trades."""
    equity = _prepare_equity_curve(equity_curve)
    returns = equity.pct_change().dropna()

    if len(equity) >= 2 and float(equity.iloc[0]) > 0:
        total_return = float(equity.iloc[-1] / equity.iloc[0] - 1.0)
        annual_return = float((equity.iloc[-1] / equity.iloc[0]) ** (trading_days / len(equity)) - 1.0)
    else:
        total_return = 0.0
        annual_return = 0.0

    max_drawdown, max_dd_start, max_dd_end = calculate_max_drawdown(equity)

    rf_daily = risk_free_rate / trading_days
    returns_std = returns.std()
    if returns.empty or pd.isna(returns_std) or returns_std == 0:
        sharpe_ratio = 0.0
    else:
        sharpe_ratio = float(((returns.mean() - rf_daily) / returns_std) * math.sqrt(trading_days))

    downside = returns[returns < 0]
    downside_std = downside.std()
    if downside.empty or pd.isna(downside_std) or downside_std == 0:
        sortino_ratio = 999.0
    else:
        sortino_ratio = float(((returns.mean() - rf_daily) / downside_std) * math.sqrt(trading_days))

    if max_drawdown == 0:
        calmar_ratio = 999.0
    else:
        calmar_ratio = float(annual_return / abs(max_drawdown))

    clean_trades = trades.copy(deep=True) if trades is not None else pd.DataFrame()
    if "pnl" not in clean_trades.columns:
        clean_trades["pnl"] = pd.Series(dtype="float64")
    pnl = pd.to_numeric(clean_trades["pnl"], errors="coerce").fillna(0.0)

    total_trades = int(len(clean_trades))
    if total_trades == 0:
        win_rate = 0.0
        profit_factor = 0.0
        max_single_loss = 0.0
    else:
        wins = int((pnl > 0).sum())
        win_rate = float(wins / total_trades)
        gains = float(pnl[pnl > 0].sum())
        losses = float(pnl[pnl < 0].sum())
        if losses == 0.0:
            profit_factor = 999.0
        else:
            profit_factor = float(gains / abs(losses))
        max_single_loss = float(pnl.min())

    avg_holding_days = _calculate_avg_holding_days(clean_trades)

    return BacktestResult(
        equity_curve=equity,
        returns=returns,
        trades=clean_trades,
        total_return=total_return,
        annual_return=annual_return,
        max_drawdown=float(max_drawdown),
        max_drawdown_start=max_dd_start,
        max_drawdown_end=max_dd_end,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        calmar_ratio=calmar_ratio,
        win_rate=win_rate,
        profit_factor=profit_factor,
        total_trades=total_trades,
        avg_holding_days=avg_holding_days,
        max_single_loss=max_single_loss,
        signals=signals,
    )


def calculate_max_drawdown(equity_curve: pd.Series) -> tuple[float, str, str]:
    """Return (max_drawdown_pct, peak_date, trough_date)."""
    equity = _prepare_equity_curve(equity_curve)
    if equity.empty:
        return 0.0, "", ""

    running_max = equity.cummax()
    drawdowns = 1.0 - (equity / running_max)
    max_drawdown = float(drawdowns.max())
    trough_date = drawdowns.idxmax()

    if max_drawdown <= 0:
        stable_date = equity.index[0]
        date_text = pd.Timestamp(stable_date).strftime("%Y-%m-%d")
        return 0.0, date_text, date_text

    equity_to_trough = equity.loc[:trough_date]
    peak_date = equity_to_trough.idxmax()
    return (
        max_drawdown,
        pd.Timestamp(peak_date).strftime("%Y-%m-%d"),
        pd.Timestamp(trough_date).strftime("%Y-%m-%d"),
    )


def calculate_monthly_returns(equity_curve: pd.Series) -> pd.DataFrame:
    """Calculate year x month return table for heatmap usage."""
    equity = _prepare_equity_curve(equity_curve)
    if equity.empty:
        return pd.DataFrame(columns=list(range(1, 13)), dtype="float64")

    month_end_equity = equity.resample("ME").last()
    monthly_returns = month_end_equity.pct_change()
    monthly_df = pd.DataFrame(
        {
            "year": monthly_returns.index.year,
            "month": monthly_returns.index.month,
            "value": monthly_returns.values,
        }
    )

    pivot = monthly_df.pivot(index="year", columns="month", values="value")
    pivot = pivot.reindex(columns=list(range(1, 13)))
    pivot = pivot.sort_index()
    return pivot.astype("float64")


def _prepare_equity_curve(equity_curve: pd.Series) -> pd.Series:
    if equity_curve is None:
        return pd.Series(dtype="float64")
    equity = pd.Series(equity_curve).copy()
    equity.index = pd.to_datetime(equity.index)
    equity = pd.to_numeric(equity, errors="coerce")
    equity = equity.dropna().sort_index()
    return equity.astype("float64")


def _calculate_avg_holding_days(trades: pd.DataFrame) -> float:
    if trades.empty or "entry_date" not in trades.columns or "exit_date" not in trades.columns:
        return 0.0

    entry = pd.to_datetime(trades["entry_date"], errors="coerce")
    exit_ = pd.to_datetime(trades["exit_date"], errors="coerce")
    holding_days = (exit_ - entry).dt.days.dropna()
    if holding_days.empty:
        return 0.0
    return float(holding_days.mean())
