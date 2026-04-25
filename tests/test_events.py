from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import json

import pytest

from src.backtest.events import BarEvent, FillEvent, OrderEvent


def _aware_dt() -> datetime:
    return datetime(2024, 1, 2, 9, 0, tzinfo=timezone.utc)


def test_bar_event_frozen() -> None:
    bar = BarEvent(
        symbol="2330",
        timestamp=_aware_dt(),
        open=100.0,
        high=101.0,
        low=99.5,
        close=100.5,
        volume=1_000,
        freq="1min",
    )
    with pytest.raises(FrozenInstanceError):
        bar.close = 999.0


def test_order_event_limit_requires_price() -> None:
    with pytest.raises(ValueError):
        OrderEvent(symbol="2330", order_type="LIMIT", side="BUY", quantity=1_000, price=None)


def test_order_event_invalid_side() -> None:
    with pytest.raises(ValueError):
        OrderEvent(symbol="2330", order_type="MARKET", side="HOLD", quantity=1_000)


def test_order_event_negative_quantity() -> None:
    with pytest.raises(ValueError):
        OrderEvent(symbol="2330", order_type="MARKET", side="BUY", quantity=-100)


def test_order_event_price_type_error() -> None:
    with pytest.raises(TypeError):
        OrderEvent(symbol="2330", order_type="LIMIT", side="BUY", quantity=100, price="50.0")


def test_fill_event_total_cost_buy() -> None:
    fill = FillEvent(
        symbol="2330",
        side="BUY",
        quantity=100,
        fill_price=50.0,
        commission=7.0,
        tax=0.0,
        timestamp=_aware_dt(),
    )
    assert fill.total_cost == pytest.approx(5007.0, abs=1e-9)


def test_fill_event_total_cost_sell() -> None:
    fill = FillEvent(
        symbol="2330",
        side="SELL",
        quantity=100,
        fill_price=50.0,
        commission=7.0,
        tax=15.0,
        timestamp=_aware_dt(),
    )
    assert fill.total_cost == pytest.approx(4978.0, abs=1e-9)


def test_events_serializable() -> None:
    events = [
        BarEvent(
            symbol="2330",
            timestamp=_aware_dt(),
            open=100.0,
            high=101.0,
            low=99.5,
            close=100.5,
            volume=1_000,
            freq="1min",
        ),
        OrderEvent(symbol="2330", order_type="MARKET", side="BUY", quantity=1_000),
        FillEvent(
            symbol="2330",
            side="BUY",
            quantity=100,
            fill_price=50.0,
            commission=7.0,
            tax=0.0,
            timestamp=_aware_dt(),
        ),
    ]
    for event in events:
        payload = event.to_dict()
        assert isinstance(payload, dict)
        json.dumps(payload, default=str)
