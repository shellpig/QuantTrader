"""Event-driven backtest engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from src.backtest.account import SimpleAccount
from src.backtest.base import BacktesterBase
from src.backtest.cost import CostCalculator
from src.backtest.events import BarEvent, FillEvent, OrderEvent
from src.backtest.metrics import BacktestResult, calculate_metrics
from src.core.config import get_config
from src.strategy.base import StrategyBase


ETF_SYMBOLS = {
    "0050",
    "0051",
    "0056",
    "006208",
    "00878",
    "00919",
}


@dataclass(frozen=True)
class _MatchContext:
    symbol: str
    is_etf: bool


class EventDrivenBacktester(BacktesterBase):
    """
    Event-driven backtest engine.

    Signal generated on bar t is executed on bar t+1 open.
    """

    def __init__(
        self,
        initial_capital: float = 1_000_000,
        cost_calculator: CostCalculator | None = None,
    ) -> None:
        self.initial_capital = float(initial_capital)
        self.cost_calculator = cost_calculator or self._build_cost_calculator_from_config()

    def run(self, strategy: StrategyBase, data: pd.DataFrame) -> BacktestResult:
        df = self._prepare_data(data)
        if df.empty:
            return calculate_metrics(pd.Series(dtype="float64"), pd.DataFrame())

        account = SimpleAccount(self.initial_capital)
        pending_orders: list[OrderEvent] = []
        equity_records: list[dict[str, Any]] = []
        trade_records: list[dict[str, Any]] = []

        bars = list(df.itertuples())
        freq = self._infer_freq(df.index)

        for bar in bars:
            bar_event, match_ctx = self._to_bar_event(bar, freq=freq)

            # Step 1: execute pending orders at current bar open.
            if pending_orders:
                for order in pending_orders:
                    fill = self._simulate_fill(order=order, bar=bar_event, match_ctx=match_ctx)
                    if fill is None:
                        continue
                    account.apply_fill(fill)
                    strategy.on_fill(fill, account)
                    trade_records.append(fill.to_dict())
                pending_orders.clear()

            # Step 2: strategy generates orders on current bar.
            new_orders = strategy.on_bar(bar_event, account) or []
            pending_orders.extend(new_orders)

            # Step 3: mark-to-market equity using current close.
            current_prices = {bar_event.symbol: bar_event.close}
            equity_records.append(
                {
                    "date": bar_event.timestamp,
                    "equity": account.get_total_value(current_prices),
                }
            )

        # Pending orders generated on the final bar are intentionally discarded.
        return self._build_result(equity_records=equity_records, trade_records=trade_records)

    @staticmethod
    def _prepare_data(data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy(deep=True)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).set_index("date")
        else:
            df.index = pd.to_datetime(df.index, errors="coerce")
            df = df[~df.index.isna()]

        for col in ("open", "high", "low", "close"):
            if col not in df.columns:
                raise ValueError(f"Input data must include '{col}' column.")
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" not in df.columns:
            df["volume"] = 0
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype("int64")

        if "symbol" not in df.columns:
            df["symbol"] = "UNKNOWN"
        df["symbol"] = df["symbol"].fillna("UNKNOWN").astype(str)

        return df.dropna(subset=["open", "high", "low", "close"]).sort_index()

    def _to_bar_event(self, bar: Any, freq: str) -> tuple[BarEvent, _MatchContext]:
        timestamp = pd.Timestamp(bar.Index)
        if timestamp.tz is None:
            timestamp = timestamp.tz_localize("UTC")

        symbol = str(getattr(bar, "symbol", "UNKNOWN") or "UNKNOWN")
        bar_event = BarEvent(
            symbol=symbol,
            timestamp=timestamp.to_pydatetime(),
            open=float(bar.open),
            high=float(bar.high),
            low=float(bar.low),
            close=float(bar.close),
            volume=int(getattr(bar, "volume", 0)),
            freq=freq,
        )
        return bar_event, _MatchContext(symbol=symbol, is_etf=self._is_etf_symbol(symbol))

    def _simulate_fill(self, order: OrderEvent, bar: BarEvent, match_ctx: _MatchContext) -> FillEvent | None:
        side = order.side.upper()
        if order.order_type == "MARKET":
            fill_price = self.cost_calculator.apply_slippage(price=bar.open, side=side)
        elif order.order_type == "LIMIT":
            if order.price is None:
                return None
            if bar.low <= float(order.price) <= bar.high:
                fill_price = float(order.price)
            else:
                return None
        else:
            raise ValueError(f"Unsupported order type: {order.order_type}")

        cost = self.cost_calculator.calculate(
            price=fill_price,
            quantity=order.quantity,
            side=side,
            is_etf=match_ctx.is_etf,
        )

        return FillEvent(
            symbol=match_ctx.symbol,
            side=side,
            quantity=order.quantity,
            fill_price=float(fill_price),
            commission=float(cost.commission),
            tax=float(cost.tax),
            timestamp=bar.timestamp,
        )

    @staticmethod
    def _build_result(equity_records: list[dict[str, Any]], trade_records: list[dict[str, Any]]) -> BacktestResult:
        if not equity_records:
            return calculate_metrics(pd.Series(dtype="float64"), pd.DataFrame())

        equity_curve = pd.Series(
            [record["equity"] for record in equity_records],
            index=pd.to_datetime([record["date"] for record in equity_records]),
            dtype="float64",
        )
        trades_df = pd.DataFrame(trade_records)
        return calculate_metrics(equity_curve=equity_curve, trades=trades_df)

    @staticmethod
    def _infer_freq(index: pd.Index) -> str:
        if len(index) < 2:
            return "1day"
        inferred = pd.infer_freq(pd.DatetimeIndex(index))
        if not inferred:
            return "1day"

        alias = inferred.upper()
        if alias in {"D", "B"}:
            return "1day"
        if alias.endswith("T"):
            value = alias[:-1] or "1"
            return f"{value}min"
        if alias == "H":
            return "60min"
        return inferred.lower()

    @staticmethod
    def _is_etf_symbol(symbol: str) -> bool:
        if symbol in ETF_SYMBOLS:
            return True
        return len(symbol) == 4 and symbol.startswith("00")

    @staticmethod
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
