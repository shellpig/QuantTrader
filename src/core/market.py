"""Market definitions and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable
import re
from typing import Literal, cast

Market = Literal["tw", "us"]


@dataclass(frozen=True)
class MarketSpec:
    market: Market
    label: str
    timezone: str
    currency: str
    lot_size: int
    volume_unit: str
    price_tick: float | None


MARKET_SPECS: dict[Market, MarketSpec] = {
    "tw": MarketSpec(
        market="tw",
        label="台股",
        timezone="Asia/Taipei",
        currency="TWD",
        lot_size=1000,
        volume_unit="shares",
        price_tick=None,
    ),
    "us": MarketSpec(
        market="us",
        label="美股",
        timezone="America/New_York",
        currency="USD",
        lot_size=1,
        volume_unit="shares",
        price_tick=0.01,
    ),
}

_TW_SYMBOL_RE = re.compile(r"^[0-9A-Z]{4,6}$")
_US_SYMBOL_RE = re.compile(r"^[A-Z0-9]+(-[A-Z0-9]+)?$")
_US_REJECTED_SUFFIXES = {"L", "TO", "HK", "T"}


def normalize_market(market: str | None = None) -> Market:
    normalized = "tw" if market is None else str(market).strip().lower()
    if normalized not in MARKET_SPECS:
        raise ValueError(f"Unknown market: {market}")
    return cast(Market, normalized)


def get_market_spec(market: str | None = None) -> MarketSpec:
    return MARKET_SPECS[normalize_market(market)]


def normalize_symbol(symbol: str, market: str | None = None) -> str:
    normalized_market = normalize_market(market)
    token = _sanitize_symbol_input(symbol)
    upper = token.upper()

    if normalized_market == "tw":
        if not _TW_SYMBOL_RE.fullmatch(upper):
            raise ValueError(f"Invalid TW symbol: {symbol}")
        return upper

    suffix_match = re.search(r"\.([A-Z0-9]+)$", upper)
    if suffix_match and suffix_match.group(1) in _US_REJECTED_SUFFIXES:
        raise ValueError(f"US-1 rejects non-US suffix ticker: {symbol}")

    normalized_us = upper.replace(".", "-")
    if not _US_SYMBOL_RE.fullmatch(normalized_us):
        raise ValueError(f"Invalid US symbol: {symbol}")
    return normalized_us


def validate_symbol(symbol: str, market: str | None = None) -> str:
    return normalize_symbol(symbol=symbol, market=market)


def assert_single_market(markets: Iterable[str | None]) -> str:
    normalized = {normalize_market(market) for market in markets}
    if not normalized:
        raise ValueError("Market context is empty.")
    if len(normalized) != 1:
        raise ValueError(f"Mixed market context is not supported in US-1: {sorted(normalized)}")
    return next(iter(normalized))


def _sanitize_symbol_input(symbol: str) -> str:
    if not isinstance(symbol, str):
        raise ValueError("Symbol must be a non-empty string.")

    normalized = symbol.strip()
    if not normalized:
        raise ValueError("Symbol must be a non-empty string.")

    if ".." in normalized or "/" in normalized or "\\" in normalized:
        raise ValueError(f"Invalid symbol path segment: {symbol}")

    if re.match(r"^[A-Za-z]:", normalized):
        raise ValueError(f"Invalid symbol path segment: {symbol}")

    if normalized.startswith(("/", "\\")):
        raise ValueError(f"Invalid symbol path segment: {symbol}")

    return normalized
