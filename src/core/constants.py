"""Shared constants used by the project."""

TAIPEI_TZ = "Asia/Taipei"

# Taiwan Stock Exchange regular session
MARKET_OPEN = "09:00"
MARKET_CLOSE = "13:30"

# Daily limit (since 2015-06-01)
PRICE_LIMIT_PCT = 0.10

# Unified output schema for fetchers
STANDARD_COLUMNS = ["date", "open", "high", "low", "close", "volume", "symbol"]
