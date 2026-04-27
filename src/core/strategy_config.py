"""Strategy preset helpers for config.yaml."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from src.core.config import get_config

_DEFAULT_MA_NAME = "MA20_MA60"


def get_strategy_presets(config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """
    Return normalized strategy presets without mutating config content.

    Rules:
    - If `strategies[]` exists and contains valid entries, use it.
    - Else if legacy `strategy` exists, convert it to one preset in-memory.
    - Else provide one default MA preset in-memory.
    """
    cfg = config if isinstance(config, dict) else get_config()
    presets = _normalize_strategies(cfg.get("strategies"))
    if presets:
        return presets

    legacy = _normalize_legacy_strategy(cfg.get("strategy"))
    if legacy is not None:
        return [legacy]

    return [_default_moving_average_preset()]


def make_strategy_label(preset: dict[str, Any]) -> str:
    name = str(preset.get("name", "")).strip() or "Unnamed"
    strategy_type = str(preset.get("type", "")).strip() or "unknown"
    return f"{name} ({strategy_type})"


def _default_moving_average_preset() -> dict[str, Any]:
    return {
        "name": _DEFAULT_MA_NAME,
        "type": "moving_average_cross",
        "params": {
            "short_window": 20,
            "long_window": 60,
        },
    }


def _normalize_strategies(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []

    presets: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for idx, item in enumerate(raw, start=1):
        normalized = _normalize_one_preset(item, fallback_name=f"Strategy_{idx}")
        if normalized is None:
            continue
        normalized["name"] = _dedupe_name(normalized["name"], used_names)
        used_names.add(normalized["name"])
        presets.append(normalized)
    return presets


def _normalize_legacy_strategy(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    candidate = {
        "name": str(raw.get("name", "")).strip() or _DEFAULT_MA_NAME,
        "type": str(raw.get("type", "moving_average_cross")).strip().lower(),
        "params": raw.get("params", {}),
    }
    return _normalize_one_preset(candidate, fallback_name=_DEFAULT_MA_NAME)


def _normalize_one_preset(raw: Any, *, fallback_name: str) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None

    name = str(raw.get("name", "")).strip() or fallback_name
    strategy_type = str(raw.get("type", "")).strip().lower()
    params = raw.get("params", {})
    if not isinstance(params, dict):
        params = {}

    if strategy_type == "moving_average_cross":
        norm_params = _normalize_moving_average_params(params)
        if norm_params is None:
            return None
        return {
            "name": name,
            "type": strategy_type,
            "params": norm_params,
        }

    if strategy_type == "dollar_cost_averaging":
        norm_params = _normalize_dca_params(params)
        if norm_params is None:
            return None
        return {
            "name": name,
            "type": strategy_type,
            "params": norm_params,
        }

    if not strategy_type:
        return None

    # Keep unsupported strategy types as-is to avoid destructive data loss
    # when users already have future presets in config.
    return {
        "name": name,
        "type": strategy_type,
        "params": deepcopy(params),
    }


def _normalize_moving_average_params(params: dict[str, Any]) -> dict[str, Any] | None:
    short_raw = params.get("short_window", params.get("ma_short", 20))
    long_raw = params.get("long_window", params.get("ma_long", 60))
    try:
        short_window = int(short_raw)
        long_window = int(long_raw)
    except (TypeError, ValueError):
        return None

    if short_window <= 0 or long_window <= 0 or short_window >= long_window:
        return None

    return {
        "short_window": short_window,
        "long_window": long_window,
    }


def _normalize_dca_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        monthly_day = int(params.get("monthly_day", 5))
        monthly_amount = float(params.get("monthly_amount", 10_000))
        min_buy_unit = int(params.get("min_buy_unit", 1))
    except (TypeError, ValueError):
        return None

    if not 1 <= monthly_day <= 31:
        return None
    if monthly_amount <= 0:
        return None
    if min_buy_unit < 1:
        return None

    non_trading_day_policy = str(params.get("non_trading_day_policy", "next_trading_day")).strip().lower()
    if non_trading_day_policy != "next_trading_day":
        non_trading_day_policy = "next_trading_day"

    buy_price_field = str(params.get("buy_price_field", "close")).strip().lower()
    if buy_price_field != "close":
        buy_price_field = "close"

    return {
        "monthly_day": monthly_day,
        "monthly_amount": monthly_amount,
        "min_buy_unit": min_buy_unit,
        "non_trading_day_policy": non_trading_day_policy,
        "buy_price_field": buy_price_field,
    }


def _dedupe_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        return name

    suffix = 2
    while True:
        candidate = f"{name}_{suffix}"
        if candidate not in used_names:
            return candidate
        suffix += 1
