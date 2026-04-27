from __future__ import annotations

import pandas as pd

from src.backtest.cost import CostCalculator
from src.backtest.dca import run_dca_backtest
from src.core.constants import TAIPEI_TZ


def _build_daily_data(dates: list[str], *, close: float, symbol: str = "2330") -> pd.DataFrame:
    ts = pd.to_datetime(dates).tz_localize(TAIPEI_TZ)
    return pd.DataFrame(
        {
            "date": ts,
            "open": [close] * len(ts),
            "high": [close] * len(ts),
            "low": [close] * len(ts),
            "close": [close] * len(ts),
            "symbol": [symbol] * len(ts),
        }
    )


def test_nonexistent_monthly_day_uses_month_end_then_next_trading_day() -> None:
    data = _build_daily_data(["2026-03-02", "2026-03-31"], close=10.0)
    result = run_dca_backtest(
        data=data,
        symbol="2330",
        start_ts=pd.Timestamp("2026-02-01", tz=TAIPEI_TZ),
        end_exclusive=pd.Timestamp("2026-04-01", tz=TAIPEI_TZ),
        params={
            "monthly_day": 31,
            "monthly_amount": 100.0,
            "min_buy_unit": 1,
            "non_trading_day_policy": "next_trading_day",
            "buy_price_field": "close",
        },
        cost_calculator=CostCalculator(slippage_ticks=0),
    )

    assert result.contribution_count == 2
    assert len(result.transactions) == 2
    assert result.transactions.iloc[0]["status"] == "FILLED"
    assert result.transactions.iloc[1]["status"] == "FILLED"
    assert pd.Timestamp(result.transactions.iloc[0]["date"]).date().isoformat() == "2026-03-02"
    assert pd.Timestamp(result.transactions.iloc[1]["date"]).date().isoformat() == "2026-03-31"


def test_skip_row_is_written_when_amount_is_insufficient_for_one_share() -> None:
    data = _build_daily_data(["2026-01-15"], close=1000.0)
    result = run_dca_backtest(
        data=data,
        symbol="2330",
        start_ts=pd.Timestamp("2026-01-01", tz=TAIPEI_TZ),
        end_exclusive=pd.Timestamp("2026-02-01", tz=TAIPEI_TZ),
        params={
            "monthly_day": 15,
            "monthly_amount": 10.0,
            "min_buy_unit": 1,
            "non_trading_day_policy": "next_trading_day",
            "buy_price_field": "close",
        },
        cost_calculator=CostCalculator(slippage_ticks=0),
    )

    assert result.contribution_count == 1
    assert len(result.transactions) == 1
    row = result.transactions.iloc[0]
    assert row["status"] == "SKIPPED"
    assert row["reason"] == "INSUFFICIENT_FOR_MIN_BUY_UNIT"
    assert int(row["buy_shares"]) == 0
    assert float(row["cash_balance"]) == 10.0


def test_skip_row_is_written_when_no_trading_day_after_target_until_month_end() -> None:
    data = _build_daily_data(["2026-01-10"], close=50.0)
    result = run_dca_backtest(
        data=data,
        symbol="2330",
        start_ts=pd.Timestamp("2026-01-01", tz=TAIPEI_TZ),
        end_exclusive=pd.Timestamp("2026-02-01", tz=TAIPEI_TZ),
        params={
            "monthly_day": 25,
            "monthly_amount": 1000.0,
            "min_buy_unit": 1,
            "non_trading_day_policy": "next_trading_day",
            "buy_price_field": "close",
        },
        cost_calculator=CostCalculator(slippage_ticks=0),
    )

    assert len(result.transactions) == 1
    row = result.transactions.iloc[0]
    assert row["status"] == "SKIPPED"
    assert row["reason"] == "NO_TRADING_DAY_UNTIL_MONTH_END"
    assert pd.Timestamp(row["date"]).date().isoformat() == "2026-01-31"
    assert float(row["cumulative_invested"]) == 1000.0
