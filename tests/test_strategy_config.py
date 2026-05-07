from __future__ import annotations

from src.core.config import clear_config_cache, get_config
from src.core.strategy_config import (
    STRATEGY_META,
    format_param_caption,
    get_strategy_meta,
    get_strategy_presets,
    make_strategy_label,
)


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


# ---------------------------------------------------------------------------
# Normalize param tests (7 tests)
# ---------------------------------------------------------------------------

def test_normalize_rsi_params_defaults() -> None:
    presets = get_strategy_presets({"strategies": [{"name": "RSI_14", "type": "rsi", "params": {}}]})
    assert len(presets) == 1
    p = presets[0]["params"]
    assert p == {"period": 14, "oversold": 30.0, "overbought": 70.0}


def test_normalize_rsi_params_invalid() -> None:
    # oversold >= overbought → filtered out → falls back to default MA preset
    presets = get_strategy_presets(
        {"strategies": [{"name": "Bad_RSI", "type": "rsi", "params": {"oversold": 80, "overbought": 70}}]}
    )
    assert presets[0]["name"] == "MA20_MA60"


def test_normalize_kd_cross_params_defaults() -> None:
    presets = get_strategy_presets({"strategies": [{"name": "KD", "type": "kd_cross", "params": {}}]})
    assert len(presets) == 1
    p = presets[0]["params"]
    assert p == {"k_period": 9, "d_period": 3, "smooth_k": 3}


def test_normalize_macd_cross_params_invalid() -> None:
    # fast >= slow → filtered out
    presets = get_strategy_presets(
        {"strategies": [{"name": "Bad_MACD", "type": "macd_cross", "params": {"fast": 30, "slow": 20}}]}
    )
    assert presets[0]["name"] == "MA20_MA60"


def test_normalize_bollinger_band_params_defaults() -> None:
    presets = get_strategy_presets({"strategies": [{"name": "BB", "type": "bollinger_band", "params": {}}]})
    assert len(presets) == 1
    p = presets[0]["params"]
    assert p == {"period": 20, "std_dev": 2.0}


def test_normalize_bias_params_invalid() -> None:
    # buy_bias >= sell_bias → filtered out
    presets = get_strategy_presets(
        {"strategies": [{"name": "Bad_Bias", "type": "bias", "params": {"buy_bias": 10.0, "sell_bias": -10.0}}]}
    )
    assert presets[0]["name"] == "MA20_MA60"


def test_normalize_donchian_breakout_params_defaults() -> None:
    presets = get_strategy_presets(
        {"strategies": [{"name": "Donchian", "type": "donchian_breakout", "params": {}}]}
    )
    assert len(presets) == 1
    p = presets[0]["params"]
    assert p == {"entry_period": 20, "exit_period": 10}


# ---------------------------------------------------------------------------
# STRATEGY_META tests (5 tests)
# ---------------------------------------------------------------------------

_ALL_STRATEGY_TYPES = {
    "moving_average_cross",
    "dollar_cost_averaging",
    "rsi",
    "kd_cross",
    "macd_cross",
    "bollinger_band",
    "bias",
    "donchian_breakout",
}

_REQUIRED_FIELDS = {"label", "description", "buy_hint", "sell_hint", "param_labels"}


def test_strategy_meta_covers_all_types() -> None:
    assert set(STRATEGY_META.keys()) == _ALL_STRATEGY_TYPES


def test_strategy_meta_has_required_fields() -> None:
    for strategy_type, meta in STRATEGY_META.items():
        missing = _REQUIRED_FIELDS - set(meta.keys())
        assert not missing, f"{strategy_type} missing fields: {missing}"
        assert isinstance(meta["param_labels"], dict)


def test_make_strategy_label_chinese() -> None:
    preset = {"name": "MA20_MA60", "type": "moving_average_cross", "params": {}}
    label = make_strategy_label(preset)
    assert label == "MA20_MA60 (均線交叉)"


def test_format_param_caption_chinese() -> None:
    caption = format_param_caption("rsi", {"period": 14, "oversold": 30.0, "overbought": 70.0})
    assert "RSI 週期" in caption
    assert "超賣門檻" in caption
    assert "超買門檻" in caption


def test_format_param_caption_unknown_type_fallback() -> None:
    # Unknown type should not crash; falls back to raw key=value format
    caption = format_param_caption("unknown_type", {"foo": 1, "bar": 2})
    assert "foo=1" in caption
    assert "bar=2" in caption


def test_config_yaml_exposes_all_8_strategy_types() -> None:
    clear_config_cache()
    presets = get_strategy_presets(get_config())
    types = {p["type"] for p in presets}
    assert types == _ALL_STRATEGY_TYPES
