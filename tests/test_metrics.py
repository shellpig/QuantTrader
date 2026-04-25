from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.backtest.metrics import calculate_max_drawdown, calculate_metrics, calculate_monthly_returns


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "known_returns.csv"


def _load_known_equity() -> pd.Series:
    df = pd.read_csv(FIXTURE_PATH)
    df["date"] = pd.to_datetime(df["date"])
    return df.set_index("date")["equity"].astype("float64")


def _mock_trades() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entry_date": pd.to_datetime(["2024-01-02", "2024-01-08", "2024-01-10"]),
            "exit_date": pd.to_datetime(["2024-01-05", "2024-01-09", "2024-01-12"]),
            "pnl": [15000.0, -8000.0, 12000.0],
        }
    )


def test_sharpe_known_returns() -> None:
    equity = _load_known_equity()
    result = calculate_metrics(equity, _mock_trades(), risk_free_rate=0.01, trading_days=252)

    assert result.total_return == pytest.approx(0.045, abs=0.001)
    assert result.sharpe_ratio == pytest.approx(6.5321437625, abs=0.001)


def test_max_drawdown_simple() -> None:
    equity = pd.Series(
        [100.0, 110.0, 90.0, 95.0],
        index=pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]),
    )

    mdd, _, _ = calculate_max_drawdown(equity)
    assert mdd == pytest.approx((110.0 - 90.0) / 110.0, abs=0.0001)


def test_max_drawdown_dates() -> None:
    equity = pd.Series(
        [100.0, 120.0, 90.0, 95.0],
        index=pd.to_datetime(["2024-02-01", "2024-02-02", "2024-02-05", "2024-02-06"]),
    )

    _, peak_date, trough_date = calculate_max_drawdown(equity)
    assert peak_date == "2024-02-02"
    assert trough_date == "2024-02-05"


def test_all_winning_edge_case() -> None:
    equity = pd.Series(
        [1000000.0, 1010000.0, 1025000.0, 1030000.0],
        index=pd.to_datetime(["2024-03-01", "2024-03-04", "2024-03-05", "2024-03-06"]),
    )
    trades = pd.DataFrame(
        {
            "entry_date": pd.to_datetime(["2024-03-01", "2024-03-04"]),
            "exit_date": pd.to_datetime(["2024-03-04", "2024-03-06"]),
            "pnl": [8000.0, 7000.0],
        }
    )

    result = calculate_metrics(equity, trades)
    assert result.max_drawdown == 0.0
    assert result.win_rate == 1.0
    assert result.profit_factor == 999.0


def test_monthly_returns_shape() -> None:
    dates = pd.bdate_range("2024-01-02", "2025-12-31")
    equity = pd.Series(
        [1_000_000.0 + i * 500.0 for i in range(len(dates))],
        index=dates,
    )

    monthly = calculate_monthly_returns(equity)
    assert monthly.shape == (2, 12)
    assert monthly.index.tolist() == [2024, 2025]
    assert monthly.columns.tolist() == list(range(1, 13))


def test_sortino_no_downside() -> None:
    equity = pd.Series(
        [100.0, 101.0, 102.0, 103.5, 104.0],
        index=pd.to_datetime(["2024-04-01", "2024-04-02", "2024-04-03", "2024-04-04", "2024-04-05"]),
    )
    trades = pd.DataFrame({"entry_date": ["2024-04-01"], "exit_date": ["2024-04-05"], "pnl": [1000.0]})

    result = calculate_metrics(equity, trades)
    assert result.sortino_ratio == 999.0
