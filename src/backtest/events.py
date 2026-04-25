"""Event objects for event-driven backtesting."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from numbers import Real
from typing import Any


def _is_real_number(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _validate_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be str.")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty.")
    return value


def _validate_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be datetime.")
    return value


def _validate_positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be int.")
    if value <= 0:
        raise ValueError(f"{field_name} must be positive.")
    return value


def _validate_non_negative_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{field_name} must be int.")
    if value < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return value


def _validate_real(value: Any, field_name: str) -> float:
    if not _is_real_number(value):
        raise TypeError(f"{field_name} must be a real number.")
    return float(value)


def _validate_non_negative_real(value: Any, field_name: str) -> float:
    number = _validate_real(value, field_name)
    if number < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return number


@dataclass(frozen=True)
class BarEvent:
    """
    Immutable OHLCV bar event.

    `timestamp` must be timezone-aware.
    """

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    freq: str

    def __post_init__(self) -> None:
        _validate_string(self.symbol, "symbol")
        timestamp = _validate_datetime(self.timestamp, "timestamp")
        if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) is None:
            raise ValueError("timestamp must be timezone-aware.")

        open_ = _validate_real(self.open, "open")
        high = _validate_real(self.high, "high")
        low = _validate_real(self.low, "low")
        close = _validate_real(self.close, "close")
        _validate_non_negative_int(self.volume, "volume")
        _validate_string(self.freq, "freq")

        if high < low:
            raise ValueError("high must be greater than or equal to low.")

        object.__setattr__(self, "open", open_)
        object.__setattr__(self, "high", high)
        object.__setattr__(self, "low", low)
        object.__setattr__(self, "close", close)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OrderEvent:
    """Order placement event."""

    symbol: str
    order_type: str
    side: str
    quantity: int
    price: float | None = None

    def __post_init__(self) -> None:
        _validate_string(self.symbol, "symbol")
        _validate_string(self.order_type, "order_type")
        _validate_string(self.side, "side")
        _validate_positive_int(self.quantity, "quantity")

        order_type = self.order_type.upper()
        side = self.side.upper()
        if order_type not in {"MARKET", "LIMIT"}:
            raise ValueError(f"Invalid order_type: {self.order_type}")
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Invalid side: {self.side}")

        if order_type == "LIMIT":
            if self.price is None:
                raise ValueError("LIMIT order must have a price.")
            price = _validate_real(self.price, "price")
            if price <= 0:
                raise ValueError("price must be positive.")
            object.__setattr__(self, "price", price)
        elif self.price is not None:
            raise ValueError("MARKET order price must be None.")

        object.__setattr__(self, "order_type", order_type)
        object.__setattr__(self, "side", side)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FillEvent:
    """Order fill event."""

    symbol: str
    side: str
    quantity: int
    fill_price: float
    commission: float
    tax: float
    timestamp: datetime

    def __post_init__(self) -> None:
        _validate_string(self.symbol, "symbol")
        _validate_string(self.side, "side")
        _validate_positive_int(self.quantity, "quantity")
        fill_price = _validate_real(self.fill_price, "fill_price")
        commission = _validate_non_negative_real(self.commission, "commission")
        tax = _validate_non_negative_real(self.tax, "tax")
        _validate_datetime(self.timestamp, "timestamp")

        side = self.side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError(f"Invalid side: {self.side}")
        if fill_price <= 0:
            raise ValueError("fill_price must be positive.")

        object.__setattr__(self, "side", side)
        object.__setattr__(self, "fill_price", fill_price)
        object.__setattr__(self, "commission", commission)
        object.__setattr__(self, "tax", tax)

    @property
    def total_cost(self) -> float:
        base = self.fill_price * self.quantity
        if self.side == "BUY":
            return float(base + self.commission)
        return float(base - self.commission - self.tax)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
