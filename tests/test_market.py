from __future__ import annotations

import pytest

from src.core.market import (
    MARKET_SPECS,
    assert_single_market,
    get_market_spec,
    normalize_symbol,
)


def test_market_specs_include_tw_and_us() -> None:
    assert "tw" in MARKET_SPECS
    assert "us" in MARKET_SPECS
    assert get_market_spec("tw").timezone == "Asia/Taipei"
    assert get_market_spec("us").timezone == "America/New_York"
    assert get_market_spec("tw").currency == "TWD"
    assert get_market_spec("us").currency == "USD"
    assert get_market_spec("tw").lot_size == 1000
    assert get_market_spec("us").lot_size == 1
    assert get_market_spec("tw").volume_unit == "shares"
    assert get_market_spec("us").volume_unit == "shares"


def test_get_market_spec_rejects_unknown_market() -> None:
    with pytest.raises(ValueError, match="Unknown market"):
        get_market_spec("crypto")


@pytest.mark.parametrize("symbol", ["2330", "00981A"])
def test_normalize_tw_symbol_keeps_existing_rules(symbol: str) -> None:
    assert normalize_symbol(symbol, market="tw") == symbol


def test_normalize_us_symbol_uppercases() -> None:
    assert normalize_symbol("aapl", market="us") == "AAPL"


def test_normalize_us_symbol_converts_class_share_dot() -> None:
    assert normalize_symbol("brk.b", market="us") == "BRK-B"


@pytest.mark.parametrize("symbol", ["7203.T", "SHOP.TO", "0700.HK"])
def test_normalize_us_symbol_rejects_foreign_suffix(symbol: str) -> None:
    with pytest.raises(ValueError, match="rejects non-US suffix"):
        normalize_symbol(symbol, market="us")


def test_assert_single_market_accepts_one_market() -> None:
    assert assert_single_market(["tw", "TW", None]) == "tw"


def test_assert_single_market_rejects_mixed_markets() -> None:
    with pytest.raises(ValueError, match="Mixed market context"):
        assert_single_market(["tw", "us"])
