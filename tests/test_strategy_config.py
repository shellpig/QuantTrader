from __future__ import annotations

from src.core.strategy_config import get_strategy_presets


def test_missing_strategies_uses_default_ma_preset() -> None:
    presets = get_strategy_presets({"ai": {"enabled": False}})

    assert len(presets) == 1
    assert presets[0]["name"] == "MA20_MA60"
    assert presets[0]["type"] == "moving_average_cross"
    assert presets[0]["params"]["short_window"] == 20
    assert presets[0]["params"]["long_window"] == 60


def test_uses_existing_strategies_list_without_disk_write() -> None:
    config = {
        "strategies": [
            {
                "name": "MA10_30",
                "type": "moving_average_cross",
                "params": {"short_window": 10, "long_window": 30},
            },
            {
                "name": "Monthly_DCA",
                "type": "dollar_cost_averaging",
                "params": {
                    "monthly_day": 25,
                    "monthly_amount": 8888,
                    "min_buy_unit": 1,
                    "non_trading_day_policy": "next_trading_day",
                    "buy_price_field": "close",
                },
            },
        ]
    }

    presets = get_strategy_presets(config)

    assert len(presets) == 2
    assert presets[0]["name"] == "MA10_30"
    assert presets[1]["type"] == "dollar_cost_averaging"
    assert config["strategies"][0]["name"] == "MA10_30"


def test_legacy_strategy_block_is_converted_in_memory() -> None:
    config = {
        "strategy": {
            "name": "LegacyMA",
            "type": "moving_average_cross",
            "params": {"ma_short": 8, "ma_long": 21},
        }
    }

    presets = get_strategy_presets(config)

    assert len(presets) == 1
    assert presets[0]["name"] == "LegacyMA"
    assert presets[0]["type"] == "moving_average_cross"
    assert presets[0]["params"] == {"short_window": 8, "long_window": 21}


def test_invalid_strategies_fall_back_to_default() -> None:
    presets = get_strategy_presets(
        {
            "strategies": [
                {"name": "Broken", "type": "moving_average_cross", "params": {"short_window": 30, "long_window": 5}}
            ]
        }
    )

    assert len(presets) == 1
    assert presets[0]["name"] == "MA20_MA60"
