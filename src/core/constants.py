"""Shared constants used by the project."""

TAIPEI_TZ = "Asia/Taipei"

# Taiwan Stock Exchange regular session
MARKET_OPEN = "09:00"
MARKET_CLOSE = "13:30"

# Daily limit (since 2015-06-01)
PRICE_LIMIT_PCT = 0.10

# Unified output schema for fetchers
STANDARD_COLUMNS = ["date", "open", "high", "low", "close", "volume", "symbol"]
SPLITS_COLUMNS = ["date", "before_price", "after_price", "symbol"]
INSTITUTIONAL_COLUMNS = [
    "date",
    "foreign_buy",
    "foreign_sell",
    "foreign_net",
    "trust_buy",
    "trust_sell",
    "trust_net",
    "dealer_buy",
    "dealer_sell",
    "dealer_net",
    "symbol",
]
MARGIN_COLUMNS = [
    "date",
    "margin_buy",
    "margin_sell",
    "margin_balance",
    "short_buy",
    "short_sell",
    "short_balance",
    "symbol",
]

# Canonical bar frequencies for event objects.
VALID_BAR_FREQS = {"1min", "5min", "15min", "30min", "60min", "1day"}
