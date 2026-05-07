"""Dedicated backtest flow for dollar-cost averaging strategy."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Any

import pandas as pd

from src.backtest.cost import CostCalculator
from src.backtest._helpers import ETF_SYMBOLS
from src.core.constants import TAIPEI_TZ
from src.core.config import get_config


@dataclass
class DcaBacktestResult:
    """Result container for DCA backtest."""

    transactions: pd.DataFrame
    cumulative_invested: float
    market_value: float
    cash_balance: float
    unrealized_pnl: float
    total_return_rate: float
    cumulative_shares: int
    average_cost: float
    contribution_count: int


def run_dca_backtest(
    *,
    data: pd.DataFrame,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    params: dict[str, Any],
    cost_calculator: CostCalculator | None = None,
) -> DcaBacktestResult:
    """Run DCA simulation with external monthly contributions."""
    if end_exclusive <= start_ts:
        raise ValueError("end_exclusive must be after start_ts.")

    monthly_day = int(params.get("monthly_day", 5))
    monthly_amount = float(params.get("monthly_amount", 10_000))
    min_buy_unit = max(1, int(params.get("min_buy_unit", 1)))
    buy_price_field = str(params.get("buy_price_field", "close")).strip().lower()
    if buy_price_field != "close":
        raise ValueError("Only buy_price_field='close' is supported.")

    calc = cost_calculator or _build_cost_calculator_from_config()
    prepared = _prepare_data(data, buy_price_field=buy_price_field)
    trading_dates = pd.DatetimeIndex(prepared["date"]).sort_values().unique()

    months = _list_schedule_months(start_ts=start_ts, end_exclusive=end_exclusive)
    if not months:
        return DcaBacktestResult(
            transactions=_empty_transactions(),
            cumulative_invested=0.0,
            market_value=0.0,
            cash_balance=0.0,
            unrealized_pnl=0.0,
            total_return_rate=0.0,
            cumulative_shares=0,
            average_cost=0.0,
            contribution_count=0,
        )

    is_etf = _is_etf_symbol(symbol)
    price_indexed = prepared.set_index("date")

    cash_balance = 0.0
    cumulative_invested = 0.0
    cumulative_shares = 0
    cumulative_spend = 0.0
    contribution_count = 0
    records: list[dict[str, Any]] = []

    for year, month in months:
        contribution_count += 1
        cash_balance += monthly_amount
        cumulative_invested += monthly_amount

        resolved = _resolve_buy_date(
            trading_dates=trading_dates,
            year=year,
            month=month,
            monthly_day=monthly_day,
        )
        record = {
            "date": pd.NaT,
            "status": "SKIPPED",
            "reason": "",
            "invested_amount": float(monthly_amount),
            "buy_price": float("nan"),
            "buy_shares": 0,
            "commission": 0.0,
            "spend": 0.0,
            "cash_balance": 0.0,
            "cumulative_shares": 0,
            "cumulative_invested": 0.0,
            "average_cost": 0.0,
        }

        if resolved["date"] is None:
            record["reason"] = str(resolved["reason"])
        else:
            buy_dt = pd.Timestamp(resolved["date"])
            if buy_dt not in price_indexed.index:
                record["date"] = buy_dt
                record["reason"] = "BUY_DATE_PRICE_MISSING"
            else:
                raw_price = pd.to_numeric(price_indexed.at[buy_dt, buy_price_field], errors="coerce")
                buy_price = float(raw_price)
                if pd.isna(raw_price) or buy_price <= 0:
                    record["date"] = buy_dt
                    record["reason"] = "INVALID_BUY_PRICE"
                else:
                    buy_shares = _max_affordable_buy_quantity(
                        cash=float(cash_balance),
                        price=buy_price,
                        min_buy_unit=min_buy_unit,
                        cost_calculator=calc,
                        is_etf=is_etf,
                    )
                    if buy_shares < min_buy_unit:
                        record["date"] = buy_dt
                        record["buy_price"] = buy_price
                        record["reason"] = "INSUFFICIENT_FOR_MIN_BUY_UNIT"
                    else:
                        cost = calc.calculate(price=buy_price, quantity=buy_shares, side="BUY", is_etf=is_etf)
                        spend = (buy_price * buy_shares) + cost.total
                        cash_balance -= spend
                        cumulative_shares += buy_shares
                        cumulative_spend += spend
                        average_cost = cumulative_spend / cumulative_shares

                        record.update(
                            {
                                "date": buy_dt,
                                "status": "FILLED",
                                "reason": "",
                                "buy_price": buy_price,
                                "buy_shares": int(buy_shares),
                                "commission": float(cost.commission),
                                "spend": float(spend),
                                "average_cost": float(average_cost),
                            }
                        )

        if pd.isna(record["date"]):
            year_end_day = calendar.monthrange(year, month)[1]
            record["date"] = pd.Timestamp(year=year, month=month, day=year_end_day, tz=TAIPEI_TZ)

        record["cash_balance"] = float(cash_balance)
        record["cumulative_shares"] = int(cumulative_shares)
        record["cumulative_invested"] = float(cumulative_invested)
        if cumulative_shares > 0 and float(record["average_cost"]) <= 0:
            record["average_cost"] = float(cumulative_spend / cumulative_shares)
        records.append(record)

    last_close = 0.0
    if not prepared.empty:
        last_close = float(pd.to_numeric(prepared[buy_price_field], errors="coerce").dropna().iloc[-1])
    market_value = float(cumulative_shares * last_close)
    unrealized_pnl = float(market_value - cumulative_spend)
    total_assets = float(market_value + cash_balance)
    total_return_rate = 0.0 if cumulative_invested <= 0 else float((total_assets - cumulative_invested) / cumulative_invested)
    average_cost = 0.0 if cumulative_shares == 0 else float(cumulative_spend / cumulative_shares)

    transactions = pd.DataFrame(records)
    return DcaBacktestResult(
        transactions=transactions,
        cumulative_invested=float(cumulative_invested),
        market_value=market_value,
        cash_balance=float(cash_balance),
        unrealized_pnl=unrealized_pnl,
        total_return_rate=total_return_rate,
        cumulative_shares=int(cumulative_shares),
        average_cost=average_cost,
        contribution_count=int(contribution_count),
    )


def _prepare_data(data: pd.DataFrame, *, buy_price_field: str) -> pd.DataFrame:
    df = data.copy(deep=True)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.to_datetime(df.index, errors="coerce")

    if buy_price_field not in df.columns:
        raise ValueError(f"Input data must include '{buy_price_field}' column.")
    df[buy_price_field] = pd.to_numeric(df[buy_price_field], errors="coerce")
    df = df.dropna(subset=["date", buy_price_field]).copy()
    if df.empty:
        return pd.DataFrame(columns=["date", buy_price_field])

    if df["date"].dt.tz is None:
        df["date"] = df["date"].dt.tz_localize(TAIPEI_TZ)
    else:
        df["date"] = df["date"].dt.tz_convert(TAIPEI_TZ)
    df["date"] = df["date"].dt.normalize()
    return df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)


def _resolve_buy_date(
    *,
    trading_dates: pd.DatetimeIndex,
    year: int,
    month: int,
    monthly_day: int,
) -> dict[str, Any]:
    if trading_dates.empty:
        return {"date": None, "reason": "NO_TRADING_DATES"}

    days_in_month = calendar.monthrange(year, month)[1]
    month_end = pd.Timestamp(date(year, month, days_in_month), tz=TAIPEI_TZ)
    if monthly_day <= days_in_month:
        start_day = pd.Timestamp(date(year, month, monthly_day), tz=TAIPEI_TZ)
        candidates = trading_dates[(trading_dates >= start_day) & (trading_dates <= month_end)]
        if len(candidates) == 0:
            return {"date": None, "reason": "NO_TRADING_DAY_UNTIL_MONTH_END"}
        return {"date": pd.Timestamp(candidates[0]), "reason": ""}

    # For non-existent monthly day (e.g., 31 in February),
    # treat month-end as base date then defer to next available trading day.
    future_candidates = trading_dates[trading_dates >= month_end]
    if len(future_candidates) == 0:
        return {"date": None, "reason": "NO_TRADING_DAY_AFTER_MONTH_END"}
    return {"date": pd.Timestamp(future_candidates[0]), "reason": ""}


def _list_schedule_months(*, start_ts: pd.Timestamp, end_exclusive: pd.Timestamp) -> list[tuple[int, int]]:
    start = pd.Timestamp(start_ts).tz_convert(TAIPEI_TZ) if pd.Timestamp(start_ts).tzinfo else pd.Timestamp(start_ts)
    end_inclusive = (pd.Timestamp(end_exclusive) - pd.Timedelta(days=1))
    if start.tzinfo is None:
        start = start.tz_localize(TAIPEI_TZ)
    else:
        start = start.tz_convert(TAIPEI_TZ)
    if end_inclusive.tzinfo is None:
        end_inclusive = end_inclusive.tz_localize(TAIPEI_TZ)
    else:
        end_inclusive = end_inclusive.tz_convert(TAIPEI_TZ)

    cur = date(start.year, start.month, 1)
    stop = date(end_inclusive.year, end_inclusive.month, 1)
    if cur > stop:
        return []

    months: list[tuple[int, int]] = []
    while cur <= stop:
        months.append((cur.year, cur.month))
        if cur.month == 12:
            cur = date(cur.year + 1, 1, 1)
        else:
            cur = date(cur.year, cur.month + 1, 1)
    return months


def _max_affordable_buy_quantity(
    *,
    cash: float,
    price: float,
    min_buy_unit: int,
    cost_calculator: CostCalculator,
    is_etf: bool,
) -> int:
    if cash <= 0 or price <= 0:
        return 0

    upper = int(cash // price)
    if upper < min_buy_unit:
        return 0

    step = max(1, int(min_buy_unit))
    upper = (upper // step) * step
    if upper < step:
        return 0

    if _buy_total_spend(price=price, quantity=upper, cost_calculator=cost_calculator, is_etf=is_etf) <= cash:
        return upper

    low_units = 1
    high_units = upper // step
    best_units = 0
    while low_units <= high_units:
        mid_units = (low_units + high_units) // 2
        quantity = mid_units * step
        spend = _buy_total_spend(price=price, quantity=quantity, cost_calculator=cost_calculator, is_etf=is_etf)
        if spend <= cash:
            best_units = mid_units
            low_units = mid_units + 1
        else:
            high_units = mid_units - 1
    return best_units * step


def _buy_total_spend(*, price: float, quantity: int, cost_calculator: CostCalculator, is_etf: bool) -> float:
    cost = cost_calculator.calculate(price=price, quantity=quantity, side="BUY", is_etf=is_etf)
    return float((price * quantity) + cost.total)


def _is_etf_symbol(symbol: str) -> bool:
    if symbol in ETF_SYMBOLS:
        return True
    return len(symbol) == 4 and symbol.startswith("00")


def _build_cost_calculator_from_config() -> CostCalculator:
    try:
        cfg = get_config().get("backtest", {})
        if not isinstance(cfg, dict):
            cfg = {}
    except Exception:
        cfg = {}

    return CostCalculator(
        commission_rate=float(cfg.get("commission_rate", 0.001425)),
        commission_discount=float(cfg.get("commission_discount", 0.6)),
        tax_rate=float(cfg.get("tax_rate", 0.003)),
        etf_tax_rate=float(cfg.get("etf_tax_rate", 0.001)),
        slippage_ticks=int(cfg.get("slippage_ticks", 1)),
    )


def _empty_transactions() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "status",
            "reason",
            "invested_amount",
            "buy_price",
            "buy_shares",
            "commission",
            "spend",
            "cash_balance",
            "cumulative_shares",
            "cumulative_invested",
            "average_cost",
        ]
    )
