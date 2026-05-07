"""Strategy preset helpers for config.yaml."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, TypedDict

from src.core.config import get_config

_DEFAULT_MA_NAME = "MA20_MA60"


# ---------------------------------------------------------------------------
# Strategy metadata
# ---------------------------------------------------------------------------

class StrategyMeta(TypedDict):
    label: str
    description: str
    buy_hint: str
    sell_hint: str
    param_labels: dict[str, str]


STRATEGY_META: dict[str, StrategyMeta] = {
    "moving_average_cross": {
        "label": "均線交叉",
        "description": "短均線上穿長均線買進，下穿賣出",
        "buy_hint": "短均線 > 長均線（黃金交叉）",
        "sell_hint": "短均線 < 長均線（死亡交叉）",
        "param_labels": {
            "short_window": "短均線週期",
            "long_window": "長均線週期",
        },
    },
    "dollar_cost_averaging": {
        "label": "定期定額",
        "description": "每月固定日期以固定金額買入",
        "buy_hint": "每月指定日自動買入",
        "sell_hint": "不主動賣出（持有至回測結束）",
        "param_labels": {
            "monthly_day": "每月投入日",
            "monthly_amount": "每月投入金額",
            "min_buy_unit": "最小買入單位（股）",
            "non_trading_day_policy": "非交易日處理",
            "buy_price_field": "買入價格欄位",
        },
    },
    "rsi": {
        "label": "RSI 超買超賣",
        "description": "RSI 低於超賣線買進，高於超買線賣出",
        "buy_hint": "RSI < 超賣門檻（如 30）",
        "sell_hint": "RSI > 超買門檻（如 70）",
        "param_labels": {
            "period": "RSI 週期",
            "oversold": "超賣門檻",
            "overbought": "超買門檻",
        },
    },
    "kd_cross": {
        "label": "KD 交叉",
        "description": "K 線上穿 D 線買進，下穿賣出",
        "buy_hint": "K 線上穿 D 線（黃金交叉）",
        "sell_hint": "K 線下穿 D 線（死亡交叉）",
        "param_labels": {
            "k_period": "K 值回看期間",
            "d_period": "D 值平滑期間",
            "smooth_k": "K 值平滑期間",
        },
    },
    "macd_cross": {
        "label": "MACD 交叉",
        "description": "MACD 上穿訊號線買進，下穿賣出",
        "buy_hint": "MACD 線上穿 Signal 線",
        "sell_hint": "MACD 線下穿 Signal 線",
        "param_labels": {
            "fast": "快線 EMA 週期",
            "slow": "慢線 EMA 週期",
            "signal": "訊號線 EMA 週期",
        },
    },
    "bollinger_band": {
        "label": "布林通道",
        "description": "跌破下軌買進，突破上軌賣出",
        "buy_hint": "收盤價跌破下軌（超跌反轉）",
        "sell_hint": "收盤價突破上軌（超漲反轉）",
        "param_labels": {
            "period": "中軌 SMA 週期",
            "std_dev": "標準差倍數",
        },
    },
    "bias": {
        "label": "乖離率",
        "description": "乖離率過低買進，過高賣出",
        "buy_hint": "BIAS < 買進門檻（如 -10%）",
        "sell_hint": "BIAS > 賣出門檻（如 10%）",
        "param_labels": {
            "ma_period": "均線週期",
            "buy_bias": "買進乖離率門檻（%）",
            "sell_bias": "賣出乖離率門檻（%）",
        },
    },
    "donchian_breakout": {
        "label": "突破策略",
        "description": "突破 N 日高點買進，跌破 M 日低點賣出",
        "buy_hint": "收盤價突破前 N 日最高價",
        "sell_hint": "收盤價跌破前 M 日最低價",
        "param_labels": {
            "entry_period": "進場回看天數",
            "exit_period": "出場回看天數",
        },
    },
}


def get_strategy_meta(strategy_type: str) -> StrategyMeta | None:
    """Return Chinese metadata for a strategy type, or None if unknown."""
    return STRATEGY_META.get(strategy_type)


def make_strategy_label(preset: dict[str, Any]) -> str:
    """Return display string for strategy selectbox: '{name} ({label})'."""
    name = str(preset.get("name", "")).strip() or "Unnamed"
    strategy_type = str(preset.get("type", "")).strip() or "unknown"
    meta = STRATEGY_META.get(strategy_type)
    label = meta["label"] if meta else strategy_type
    return f"{name} ({label})"


def format_param_caption(strategy_type: str, params: dict[str, Any]) -> str:
    """Format strategy params with Chinese labels for st.caption display."""
    meta = STRATEGY_META.get(strategy_type)
    if meta is None:
        return ", ".join(f"{k}={v}" for k, v in params.items())
    param_labels = meta["param_labels"]
    parts = [f"{param_labels.get(k, k)}={v}" for k, v in params.items()]
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# Preset loading
# ---------------------------------------------------------------------------

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

    _normalizers = {
        "moving_average_cross": _normalize_moving_average_params,
        "dollar_cost_averaging": _normalize_dca_params,
        "rsi": _normalize_rsi_params,
        "kd_cross": _normalize_kd_cross_params,
        "macd_cross": _normalize_macd_cross_params,
        "bollinger_band": _normalize_bollinger_band_params,
        "bias": _normalize_bias_params,
        "donchian_breakout": _normalize_donchian_breakout_params,
    }

    if strategy_type in _normalizers:
        norm_params = _normalizers[strategy_type](params)
        if norm_params is None:
            return None
        return {"name": name, "type": strategy_type, "params": norm_params}

    if not strategy_type:
        return None

    # Keep unsupported strategy types as-is to avoid destructive data loss
    # when users already have future presets in config.
    return {
        "name": name,
        "type": strategy_type,
        "params": deepcopy(params),
    }


# ---------------------------------------------------------------------------
# Parameter normalizers
# ---------------------------------------------------------------------------

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

    return {"short_window": short_window, "long_window": long_window}


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


def _normalize_rsi_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        period = int(params.get("period", 14))
        oversold = float(params.get("oversold", 30))
        overbought = float(params.get("overbought", 70))
    except (TypeError, ValueError):
        return None

    if period <= 0:
        return None
    if not (0 <= oversold < overbought <= 100):
        return None

    return {"period": period, "oversold": oversold, "overbought": overbought}


def _normalize_kd_cross_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        k_period = int(params.get("k_period", 9))
        d_period = int(params.get("d_period", 3))
        smooth_k = int(params.get("smooth_k", 3))
    except (TypeError, ValueError):
        return None

    if k_period <= 0 or d_period <= 0 or smooth_k <= 0:
        return None

    return {"k_period": k_period, "d_period": d_period, "smooth_k": smooth_k}


def _normalize_macd_cross_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        signal = int(params.get("signal", 9))
    except (TypeError, ValueError):
        return None

    if fast <= 0 or slow <= 0 or signal <= 0:
        return None
    if fast >= slow:
        return None

    return {"fast": fast, "slow": slow, "signal": signal}


def _normalize_bollinger_band_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        period = int(params.get("period", 20))
        std_dev = float(params.get("std_dev", 2.0))
    except (TypeError, ValueError):
        return None

    if period <= 0 or std_dev <= 0:
        return None

    return {"period": period, "std_dev": std_dev}


def _normalize_bias_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        ma_period = int(params.get("ma_period", 20))
        buy_bias = float(params.get("buy_bias", -10.0))
        sell_bias = float(params.get("sell_bias", 10.0))
    except (TypeError, ValueError):
        return None

    if ma_period <= 0:
        return None
    if buy_bias >= sell_bias:
        return None

    return {"ma_period": ma_period, "buy_bias": buy_bias, "sell_bias": sell_bias}


def _normalize_donchian_breakout_params(params: dict[str, Any]) -> dict[str, Any] | None:
    try:
        entry_period = int(params.get("entry_period", 20))
        exit_period = int(params.get("exit_period", 10))
    except (TypeError, ValueError):
        return None

    if entry_period <= 0 or exit_period <= 0:
        return None

    return {"entry_period": entry_period, "exit_period": exit_period}


def _dedupe_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        return name

    suffix = 2
    while True:
        candidate = f"{name}_{suffix}"
        if candidate not in used_names:
            return candidate
        suffix += 1
