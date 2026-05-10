"""Settings page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from src.core.config import clear_config_cache, get_config, get_project_root
from src.core.strategy_config import (
    DEFAULT_STRATEGY_PRESETS,
    SUPPORTED_STRATEGY_TYPES,
    format_param_caption,
    get_strategy_presets,
    make_strategy_label,
    make_strategy_type_label,
    normalize_strategy_preset,
)


def render() -> None:
    st.title("設定")
    if "restore_success_msg" in st.session_state:
        st.success(st.session_state.pop("restore_success_msg"))
    st.caption("調整外觀、AI、回測與風控參數，並儲存為預設。")

    config = get_config()
    ui = config.get("ui", {}) if isinstance(config, dict) else {}
    ai = config.get("ai", {}) if isinstance(config, dict) else {}
    risk = config.get("risk", {}) if isinstance(config, dict) else {}
    backtest = config.get("backtest", {}) if isinstance(config, dict) else {}
    secrets = config.get("secrets", {}) if isinstance(config, dict) else {}
    strategy_presets = get_strategy_presets(config)

    # ── 外觀 ──────────────────────────────────────────────────────────────
    st.subheader("外觀")
    theme_options = ["arctic_light", "obsidian_dark", "finance_green", "midnight_blue", "cyberpunk", "warm_sepia"]
    current_theme = str(ui.get("theme", "midnight_blue")).strip()
    if current_theme not in theme_options:
        current_theme = "midnight_blue"
    theme = st.selectbox("主題", options=theme_options, index=theme_options.index(current_theme))
    from src.ui.themes import render_theme_css
    st.markdown(render_theme_css(theme), unsafe_allow_html=True)

    current_use_extras = bool(ui.get("use_extras", True))
    use_extras = st.toggle("使用 streamlit-extras 元件", value=current_use_extras)
    current_use_option_menu = bool(ui.get("use_option_menu", True))
    use_option_menu = st.toggle("使用 option_menu 側邊欄", value=current_use_option_menu)

    # ── AI 設定 ───────────────────────────────────────────────────────────
    st.subheader("AI 設定")
    ai_enabled = st.toggle("啟用 AI 問答（ai.enabled）", value=bool(ai.get("enabled", False)))
    provider_options = ["anthropic", "openai", "gemini"]
    provider_default = str(ai.get("provider", "anthropic")).strip().lower()
    if provider_default not in provider_options:
        provider_default = "anthropic"
    provider = st.selectbox("AI Provider", options=provider_options, index=provider_options.index(provider_default))
    model = st.text_input("Model ID", value=str(ai.get("model", "")))

    # ── API Keys ──────────────────────────────────────────────────────────
    st.subheader("API Keys")
    openai_key = st.text_input("OPENAI_API_KEY", value=str(secrets.get("openai_api_key", "")), type="password")
    anthropic_key = st.text_input("ANTHROPIC_API_KEY", value=str(secrets.get("anthropic_api_key", "")), type="password")
    gemini_key = st.text_input("GEMINI_API_KEY", value=str(secrets.get("gemini_api_key", "")), type="password")

    # ── 風控參數 ──────────────────────────────────────────────────────────
    st.subheader("風控參數")
    max_daily_loss_pct = st.number_input(
        "max_daily_loss_pct",
        min_value=0.0, max_value=1.0,
        value=float(risk.get("max_daily_loss_pct", 0.03)),
        step=0.005, format="%.4f",
    )
    max_position_pct = st.number_input(
        "max_position_pct",
        min_value=0.0, max_value=1.0,
        value=float(risk.get("max_position_pct", 0.20)),
        step=0.01, format="%.4f",
    )
    max_drawdown_warning_pct = st.number_input(
        "max_drawdown_warning_pct",
        min_value=0.0, max_value=1.0,
        value=float(risk.get("max_drawdown_warning_pct", 0.10)),
        step=0.01, format="%.4f",
    )

    # ── 回測參數 ──────────────────────────────────────────────────────────
    st.subheader("回測參數")
    initial_capital = st.number_input(
        "initial_capital",
        min_value=10000.0, max_value=1_000_000_000.0,
        value=float(backtest.get("initial_capital", 1_000_000)),
        step=10000.0, format="%.0f",
    )

    # ── 一般設定按鈕（策略以外） ──────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        save_settings_clicked = st.button("儲存設定", type="primary", width="stretch")
    with col2:
        restore_settings_clicked = st.button("恢復設定預設值", width="stretch")

    if save_settings_clicked:
        try:
            _save_non_strategy_config_and_env(
                theme=theme, use_extras=use_extras, use_option_menu=use_option_menu,
                ai_enabled=ai_enabled, provider=provider, model=model,
                max_daily_loss_pct=max_daily_loss_pct,
                max_position_pct=max_position_pct,
                max_drawdown_warning_pct=max_drawdown_warning_pct,
                initial_capital=initial_capital,
                openai_key=openai_key, anthropic_key=anthropic_key, gemini_key=gemini_key,
            )
            clear_config_cache()
            st.success("設定已儲存。")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"儲存失敗：{exc}")

    if restore_settings_clicked:
        _restore_non_strategy_defaults_and_env()
        clear_config_cache()
        st.session_state["restore_success_msg"] = "已恢復設定預設值（策略清單保留）。"
        st.rerun()

    # ── 策略設定 ──────────────────────────────────────────────────────────
    st.subheader("策略設定")
    st.caption("採用「策略類型 → 對應參數表單」架構，儲存於 config.yaml 的 strategies[]。")

    strategy_select_options = ["新增策略"] + [make_strategy_label(preset) for preset in strategy_presets]
    selected_label = st.selectbox(
        "編輯策略",
        options=strategy_select_options,
        index=1 if len(strategy_select_options) > 1 else 0,
    )
    is_new_strategy = selected_label == "新增策略"
    selected_existing_name: str | None = None

    if is_new_strategy:
        selected_strategy: dict[str, Any] = {
            "name": _next_strategy_name(strategy_presets, base="NewStrategy"),
            "type": "moving_average_cross",
            "params": {"short_window": 20, "long_window": 60},
        }
    else:
        selected_idx = strategy_select_options.index(selected_label) - 1
        selected_strategy = strategy_presets[selected_idx]
        selected_existing_name = str(selected_strategy.get("name", "")).strip() or None

    strategy_name = st.text_input("策略名稱", value=str(selected_strategy.get("name", "")).strip())

    strategy_type_default = str(selected_strategy.get("type", "moving_average_cross")).strip().lower()
    if strategy_type_default not in SUPPORTED_STRATEGY_TYPES:
        strategy_type_default = "moving_average_cross"
    strategy_type = st.selectbox(
        "策略類型",
        options=SUPPORTED_STRATEGY_TYPES,
        index=SUPPORTED_STRATEGY_TYPES.index(strategy_type_default),
        format_func=make_strategy_type_label,
    )

    params = selected_strategy.get("params", {})
    if not isinstance(params, dict):
        params = {}
    edited_strategy = _render_strategy_params_form(strategy_name, strategy_type, params)

    # ── 策略按鈕 ─────────────────────────────────────────────────────────
    scol1, scol2 = st.columns(2)
    with scol1:
        save_strategy_clicked = st.button("儲存策略", type="primary", width="stretch")
    with scol2:
        restore_strategy_clicked = st.button("恢復策略預設值", width="stretch")

    if save_strategy_clicked:
        try:
            normalized_edited = normalize_strategy_preset(edited_strategy)
            merged_strategies = _merge_strategy_presets(
                existing=strategy_presets,
                edited=normalized_edited,
                replace_name=selected_existing_name,
            )
            _save_strategy_presets(merged_strategies)
            clear_config_cache()
            st.success("策略已儲存。")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"儲存失敗：{exc}")

    if restore_strategy_clicked:
        _restore_strategy_defaults()
        clear_config_cache()
        st.session_state["restore_success_msg"] = "已恢復策略預設值。"
        st.rerun()

    # ── 目前策略清單（含單筆清除） ─────────────────────────────────────
    st.subheader("目前策略清單")
    if not strategy_presets:
        st.info("目前無已儲存策略。")
    for preset in strategy_presets:
        pname = str(preset.get("name", "")).strip()
        pcol_del, pcol_info = st.columns([1, 8])
        with pcol_del:
            if st.button("清除", key=f"del_{pname}", width="stretch"):
                _delete_strategy_preset(pname)
                clear_config_cache()
                st.session_state["restore_success_msg"] = f"已清除策略：{pname}"
                st.rerun()
        with pcol_info:
            caption = format_param_caption(preset.get("type", ""), preset.get("params", {}))
            st.markdown(f"**{pname}** `{preset.get('type', '')}` — {caption}")

    # ── 當前設定快照 ──────────────────────────────────────────────────────
    try:
        preview_edited = normalize_strategy_preset(edited_strategy)
        preview_strategies = _merge_strategy_presets(
            existing=strategy_presets,
            edited=preview_edited,
            replace_name=selected_existing_name,
        )
    except Exception:
        preview_strategies = strategy_presets
    st.subheader("當前設定快照")
    st.json(
        {
            "ui": {"theme": theme, "use_extras": use_extras, "use_option_menu": use_option_menu},
            "ai": {"enabled": ai_enabled, "provider": provider, "model": model},
            "risk": {
                "max_daily_loss_pct": max_daily_loss_pct,
                "max_position_pct": max_position_pct,
                "max_drawdown_warning_pct": max_drawdown_warning_pct,
            },
            "backtest": {"initial_capital": initial_capital},
            "strategies_preview": preview_strategies,
        },
        expanded=False,
    )


# ── 策略參數表單渲染 ──────────────────────────────────────────────────────


def _render_strategy_params_form(
    strategy_name: str,
    strategy_type: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    name = strategy_name.strip()

    if strategy_type == "moving_average_cross":
        short_window = int(st.number_input("short_window", min_value=2, max_value=120, value=int(params.get("short_window", 20))))
        long_window = int(st.number_input("long_window", min_value=3, max_value=240, value=int(params.get("long_window", 60))))
        if short_window >= long_window:
            st.warning("short_window 必須小於 long_window。")
        return {"name": name, "type": strategy_type, "params": {"short_window": short_window, "long_window": long_window}}

    if strategy_type == "dollar_cost_averaging":
        monthly_day = int(st.number_input("monthly_day", min_value=1, max_value=31, value=int(params.get("monthly_day", 5))))
        monthly_amount = float(st.number_input("monthly_amount", min_value=1.0, max_value=1_000_000_000.0, value=float(params.get("monthly_amount", 10_000.0)), step=1000.0))
        min_buy_unit = int(st.number_input("min_buy_unit", min_value=1, max_value=1000, value=int(params.get("min_buy_unit", 1))))
        non_trading_day_policy = st.selectbox("non_trading_day_policy", options=["next_trading_day"], index=0)
        buy_price_field = st.selectbox("buy_price_field", options=["close"], index=0)
        return {"name": name, "type": strategy_type, "params": {"monthly_day": monthly_day, "monthly_amount": monthly_amount, "min_buy_unit": min_buy_unit, "non_trading_day_policy": non_trading_day_policy, "buy_price_field": buy_price_field}}

    if strategy_type == "rsi":
        period = int(st.number_input("period（RSI週期）", min_value=2, max_value=100, value=int(params.get("period", 14))))
        oversold = float(st.number_input("oversold（超賣門檻）", min_value=0.0, max_value=100.0, value=float(params.get("oversold", 30.0)), step=1.0))
        overbought = float(st.number_input("overbought（超買門檻）", min_value=0.0, max_value=100.0, value=float(params.get("overbought", 70.0)), step=1.0))
        if oversold >= overbought:
            st.warning("oversold 必須小於 overbought。")
        return {"name": name, "type": strategy_type, "params": {"period": period, "oversold": oversold, "overbought": overbought}}

    if strategy_type == "kd_cross":
        k_period = int(st.number_input("k_period（K值回看期間）", min_value=2, max_value=100, value=int(params.get("k_period", 9))))
        d_period = int(st.number_input("d_period（D值平滑期間）", min_value=1, max_value=20, value=int(params.get("d_period", 3))))
        smooth_k = int(st.number_input("smooth_k（K值平滑期間）", min_value=1, max_value=20, value=int(params.get("smooth_k", 3))))
        return {"name": name, "type": strategy_type, "params": {"k_period": k_period, "d_period": d_period, "smooth_k": smooth_k}}

    if strategy_type == "macd_cross":
        fast = int(st.number_input("fast（快線EMA週期）", min_value=2, max_value=100, value=int(params.get("fast", 12))))
        slow = int(st.number_input("slow（慢線EMA週期）", min_value=3, max_value=200, value=int(params.get("slow", 26))))
        signal = int(st.number_input("signal（訊號線EMA週期）", min_value=1, max_value=50, value=int(params.get("signal", 9))))
        if fast >= slow:
            st.warning("fast 必須小於 slow。")
        return {"name": name, "type": strategy_type, "params": {"fast": fast, "slow": slow, "signal": signal}}

    if strategy_type == "bollinger_band":
        period = int(st.number_input("period（中軌SMA週期）", min_value=2, max_value=200, value=int(params.get("period", 20))))
        std_dev = float(st.number_input("std_dev（標準差倍數）", min_value=0.1, max_value=10.0, value=float(params.get("std_dev", 2.0)), step=0.1, format="%.1f"))
        return {"name": name, "type": strategy_type, "params": {"period": period, "std_dev": std_dev}}

    if strategy_type == "bias":
        ma_period = int(st.number_input("ma_period（均線週期）", min_value=2, max_value=200, value=int(params.get("ma_period", 20))))
        buy_bias = float(st.number_input("buy_bias（買進乖離率門檻%）", min_value=-100.0, max_value=0.0, value=float(params.get("buy_bias", -10.0)), step=1.0))
        sell_bias = float(st.number_input("sell_bias（賣出乖離率門檻%）", min_value=0.0, max_value=100.0, value=float(params.get("sell_bias", 10.0)), step=1.0))
        if buy_bias >= sell_bias:
            st.warning("buy_bias 必須小於 sell_bias。")
        return {"name": name, "type": strategy_type, "params": {"ma_period": ma_period, "buy_bias": buy_bias, "sell_bias": sell_bias}}

    if strategy_type == "donchian_breakout":
        entry_period = int(st.number_input("entry_period（進場回看天數）", min_value=2, max_value=200, value=int(params.get("entry_period", 20))))
        exit_period = int(st.number_input("exit_period（出場回看天數）", min_value=1, max_value=200, value=int(params.get("exit_period", 10))))
        return {"name": name, "type": strategy_type, "params": {"entry_period": entry_period, "exit_period": exit_period}}

    return {"name": name, "type": strategy_type, "params": {}}


# ── config 儲存 helper ───────────────────────────────────────────────────


def _save_non_strategy_config_and_env(
    *,
    theme: str,
    use_extras: bool,
    use_option_menu: bool,
    ai_enabled: bool,
    provider: str,
    model: str,
    max_daily_loss_pct: float,
    max_position_pct: float,
    max_drawdown_warning_pct: float,
    initial_capital: float,
    openai_key: str,
    anthropic_key: str,
    gemini_key: str,
) -> None:
    """只寫 ui、ai、risk、backtest 與 .env，不改 strategies / strategy。"""
    root = get_project_root()
    config_path = root / "config.yaml"
    env_path = root / ".env"

    config = get_config().copy()
    config.pop("secrets", None)
    if "ui" not in config or not isinstance(config["ui"], dict):
        config["ui"] = {}
    if "ai" not in config or not isinstance(config["ai"], dict):
        config["ai"] = {}
    if "risk" not in config or not isinstance(config["risk"], dict):
        config["risk"] = {}
    if "backtest" not in config or not isinstance(config["backtest"], dict):
        config["backtest"] = {}

    config["ui"]["theme"] = str(theme).strip()
    config["ui"]["use_extras"] = bool(use_extras)
    config["ui"]["use_option_menu"] = bool(use_option_menu)
    config["ai"]["enabled"] = bool(ai_enabled)
    config["ai"]["provider"] = str(provider).strip().lower()
    config["ai"]["model"] = str(model).strip()
    config["risk"]["max_daily_loss_pct"] = float(max_daily_loss_pct)
    config["risk"]["max_position_pct"] = float(max_position_pct)
    config["risk"]["max_drawdown_warning_pct"] = float(max_drawdown_warning_pct)
    config["backtest"]["initial_capital"] = float(initial_capital)

    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    _write_env(env_path, {"OPENAI_API_KEY": openai_key, "ANTHROPIC_API_KEY": anthropic_key, "GEMINI_API_KEY": gemini_key})


def _restore_non_strategy_defaults_and_env() -> None:
    """只恢復策略以外設定，不改 strategies / strategy。"""
    root = get_project_root()
    config_path = root / "config.yaml"
    if not config_path.exists():
        return
    config = get_config().copy()
    config.pop("secrets", None)
    config.pop("ui", None)
    config.pop("ai", None)
    config.pop("risk", None)
    config.pop("backtest", None)
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _save_strategy_presets(strategies: list[dict[str, Any]]) -> None:
    """只寫 strategies[]，並移除舊版 strategy 區塊；不改其他 config 區塊與 .env。"""
    root = get_project_root()
    config_path = root / "config.yaml"
    config = get_config().copy()
    config.pop("secrets", None)
    config["strategies"] = strategies
    config.pop("strategy", None)
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _restore_strategy_defaults() -> None:
    """只把 strategies[] 寫成 DEFAULT_STRATEGY_PRESETS。"""
    _save_strategy_presets(list(DEFAULT_STRATEGY_PRESETS))


def _delete_strategy_preset(name: str) -> None:
    """只刪除指定 preset name，保留其他 preset 與非策略設定。"""
    config = get_config()
    current = get_strategy_presets(config)
    updated = [p for p in current if str(p.get("name", "")).strip() != name]
    _save_strategy_presets(updated)


# ── 策略合併工具 ─────────────────────────────────────────────────────────


def _merge_strategy_presets(
    *,
    existing: list[dict[str, Any]],
    edited: dict[str, Any],
    replace_name: str | None,
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    replaced = False

    for preset in existing:
        current_name = str(preset.get("name", "")).strip()
        if replace_name and current_name == replace_name:
            updated.append(edited)
            replaced = True
        elif current_name == edited["name"]:
            updated.append(edited)
            replaced = True
        else:
            updated.append(preset)

    if not replaced:
        updated.append(edited)

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for preset in updated:
        name = str(preset.get("name", "")).strip() or _next_strategy_name(deduped, base="Strategy")
        if name in seen:
            name = _next_strategy_name(deduped, base=name)
        seen.add(name)
        deduped.append({"name": name, "type": preset.get("type", ""), "params": preset.get("params", {})})
    return deduped


def _next_strategy_name(strategies: list[dict[str, Any]], *, base: str) -> str:
    used = {str(item.get("name", "")).strip() for item in strategies}
    if base not in used:
        return base
    suffix = 2
    while True:
        candidate = f"{base}_{suffix}"
        if candidate not in used:
            return candidate
        suffix += 1


def _write_env(path: Path, updates: dict[str, str]) -> None:
    current_lines: list[str]
    if path.exists():
        current_lines = path.read_text(encoding="utf-8").splitlines()
    else:
        current_lines = []

    by_key: dict[str, str] = {}
    for line in current_lines:
        if not line or line.lstrip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        by_key[key.strip()] = value

    for key, value in updates.items():
        by_key[key] = str(value).strip()

    rendered = [f"{key}={value}" for key, value in sorted(by_key.items())]
    path.write_text("\n".join(rendered) + "\n", encoding="utf-8")


if __name__ == "__main__":
    render()
