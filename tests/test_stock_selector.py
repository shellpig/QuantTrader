from __future__ import annotations

import pandas as pd

from src.ui.stock_selector import StockOption, find_stock_matches, format_stock_option, normalize_stock_options


def test_normalize_stock_options_keeps_symbol_and_name() -> None:
    raw = pd.DataFrame(
        {
            "symbol": ["2330", "00981a", "bad"],
            "name": ["台積電", "主動統一台股增長", "錯誤"],
        }
    )

    options = normalize_stock_options(raw)

    assert StockOption(symbol="2330", name="台積電") in options
    assert StockOption(symbol="00981A", name="主動統一台股增長") in options
    assert all(option.symbol != "BAD" for option in options)


def test_find_stock_matches_by_partial_name_and_symbol() -> None:
    options = [
        StockOption(symbol="2330", name="台積電"),
        StockOption(symbol="2303", name="聯電"),
        StockOption(symbol="00981A", name="主動統一台股增長"),
    ]

    assert find_stock_matches("積", options) == [StockOption(symbol="2330", name="台積電")]
    assert find_stock_matches("00981", options) == [StockOption(symbol="00981A", name="主動統一台股增長")]
    assert format_stock_option(options[0]) == "台積電（2330）"
