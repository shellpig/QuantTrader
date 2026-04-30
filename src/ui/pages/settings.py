"""Settings page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from src.core.config import clear_config_cache, get_config, get_project_root
from src.core.strategy_config import get_strategy_presets, make_strategy_label


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

    st.subheader("外觀")
    theme_options = ["arctic_light", "obsidian_dark", "finance_green", "midnight_blue", "cyberpunk", "warm_sepia"]
    current_theme = str(ui.get("theme", "arctic_light")).strip()
    if current_theme not in theme_options:
        current_theme = "arctic_light"
    theme = st.selectbox("主題", options=theme_options, index=theme_options.index(current_theme))
    from src.ui.themes import render_theme_css
    st.markdown(render_theme_css(theme), unsafe_allow_html=True)
    
    current_use_extras = bool(ui.get("use_extras", True))
    use_extras = st.toggle("使用 streamlit-extras 元件", value=current_use_extras)
    current_use_option_menu = bool(ui.get("use_option_menu", True))
    use_option_menu = st.toggle("使用 option_menu 側邊欄", value=current_use_option_menu)

    st.subheader("AI 設定")
    ai_enabled = st.toggle("啟用 AI 問答（ai.enabled）", value=bool(ai.get("enabled", False)))
    provider_options = ["anthropic", "openai", "gemini"]
    provider_default = str(ai.get("provider", "anthropic")).strip().lower()
    if provider_default not in provider_options:
        provider_default = "anthropic"
    provider = st.selectbox("AI Provider", options=provider_options, index=provider_options.index(provider_default))
    model = st.text_input("Model ID", value=str(ai.get("model", "")))

    st.subheader("API Keys")
    openai_key = st.text_input("OPENAI_API_KEY", value=str(secrets.get("openai_api_key", "")), type="password")
    anthropic_key = st.text_input("ANTHROPIC_API_KEY", value=str(secrets.get("anthropic_api_key", "")), type="password")
    gemini_key = st.text_input("GEMINI_API_KEY", value=str(secrets.get("gemini_api_key", "")), type="password")

    st.subheader("風控參數")
    max_daily_loss_pct = st.number_input(
        "max_daily_loss_pct",
        min_value=0.0,
        max_value=1.0,
        value=float(risk.get("max_daily_loss_pct", 0.03)),
        step=0.005,
        format="%.4f",
    )
    max_position_pct = st.number_input(
        "max_position_pct",
        min_value=0.0,
        max_value=1.0,
        value=float(risk.get("max_position_pct", 0.20)),
        step=0.01,
        format="%.4f",
    )
    max_drawdown_warning_pct = st.number_input(
        "max_drawdown_warning_pct",
        min_value=0.0,
        max_value=1.0,
        value=float(risk.get("max_drawdown_warning_pct", 0.10)),
        step=0.01,
        format="%.4f",
    )

    st.subheader("回測參數")
    initial_capital = st.number_input(
        "initial_capital",
        min_value=10000.0,
        max_value=1_000_000_000.0,
        value=float(backtest.get("initial_capital", 1_000_000)),
        step=10000.0,
        format="%.0f",
    )

    st.subheader("策略設定")
    st.caption("採用「策略類型 → 對應參數表單」架構，儲存於 config.yaml 的 strategies[]。")

    strategy_select_options = ["新增策略"] + [make_strategy_label(preset) for preset in strategy_presets]
    selected_label = st.selectbox("編輯策略", options=strategy_select_options, index=1 if len(strategy_select_options) > 1 else 0)
    is_new_strategy = selected_label == "新增策略"
    selected_existing_name: str | None = None

    if is_new_strategy:
        selected_strategy = {
            "name": _next_strategy_name(strategy_presets, base="NewStrategy"),
            "type": "moving_average_cross",
            "params": {"short_window": 20, "long_window": 60},
        }
    else:
        selected_idx = strategy_select_options.index(selected_label) - 1
        selected_strategy = strategy_presets[selected_idx]
        selected_existing_name = str(selected_strategy.get("name", "")).strip() or None

    strategy_name = st.text_input("策略名稱", value=str(selected_strategy.get("name", "")).strip())
    strategy_type_options = ["moving_average_cross", "dollar_cost_averaging"]
    strategy_type_default = str(selected_strategy.get("type", "moving_average_cross")).strip().lower()
    if strategy_type_default not in strategy_type_options:
        strategy_type_default = "moving_average_cross"
    strategy_type = st.selectbox(
        "策略類型",
        options=strategy_type_options,
        index=strategy_type_options.index(strategy_type_default),
    )

    params = selected_strategy.get("params", {}) if isinstance(selected_strategy.get("params"), dict) else {}
    if strategy_type == "moving_average_cross":
        short_window = int(st.number_input("short_window", min_value=2, max_value=120, value=int(params.get("short_window", 20))))
        long_window = int(st.number_input("long_window", min_value=3, max_value=240, value=int(params.get("long_window", 60))))
        if short_window >= long_window:
            st.warning("short_window 必須小於 long_window。")
        edited_strategy = {
            "name": strategy_name.strip(),
            "type": strategy_type,
            "params": {
                "short_window": short_window,
                "long_window": long_window,
            },
        }
    else:
        monthly_day = int(st.number_input("monthly_day", min_value=1, max_value=31, value=int(params.get("monthly_day", 5))))
        monthly_amount = float(
            st.number_input(
                "monthly_amount",
                min_value=1.0,
                max_value=1_000_000_000.0,
                value=float(params.get("monthly_amount", 10_000.0)),
                step=1000.0,
            )
        )
        min_buy_unit = int(st.number_input("min_buy_unit", min_value=1, max_value=1000, value=int(params.get("min_buy_unit", 1))))
        non_trading_day_policy = st.selectbox(
            "non_trading_day_policy",
            options=["next_trading_day"],
            index=0,
        )
        buy_price_field = st.selectbox(
            "buy_price_field",
            options=["close"],
            index=0,
        )

        edited_strategy = {
            "name": strategy_name.strip(),
            "type": strategy_type,
            "params": {
                "monthly_day": monthly_day,
                "monthly_amount": monthly_amount,
                "min_buy_unit": min_buy_unit,
                "non_trading_day_policy": non_trading_day_policy,
                "buy_price_field": buy_price_field,
            },
        }

    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        save_clicked = st.button("儲存", type="primary", use_container_width=True)
    with btn_col2:
        restore_clicked = st.button("恢復預設值", use_container_width=True)

    if save_clicked:
        try:
            normalized_edited = _normalize_edited_strategy(edited_strategy)
            merged_strategies = _merge_strategy_presets(
                existing=strategy_presets,
                edited=normalized_edited,
                replace_name=selected_existing_name,
            )
            _save_config_and_env(
                theme=theme,
                use_extras=use_extras,
                use_option_menu=use_option_menu,
                ai_enabled=ai_enabled,
                provider=provider,
                model=model,
                max_daily_loss_pct=max_daily_loss_pct,
                max_position_pct=max_position_pct,
                max_drawdown_warning_pct=max_drawdown_warning_pct,
                initial_capital=initial_capital,
                strategies=merged_strategies,
                openai_key=openai_key,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
            )
            clear_config_cache()
            st.success("設定已儲存。")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"儲存失敗：{exc}")

    if restore_clicked:
        _confirm_restore_dialog()

    st.subheader("目前策略清單")
    strategy_table_rows = [
        {
            "name": preset.get("name", ""),
            "type": preset.get("type", ""),
            "params": yaml.safe_dump(preset.get("params", {}), allow_unicode=True, sort_keys=False).strip(),
        }
        for preset in strategy_presets
    ]
    st.dataframe(strategy_table_rows, use_container_width=True, hide_index=True)

    try:
        preview_edited = _normalize_edited_strategy(edited_strategy)
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


def _normalize_edited_strategy(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name", "")).strip()
    if not name:
        raise ValueError("策略名稱不可為空。")

    strategy_type = str(raw.get("type", "")).strip().lower()
    params = raw.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("策略參數格式錯誤。")

    if strategy_type == "moving_average_cross":
        short_window = int(params.get("short_window", 20))
        long_window = int(params.get("long_window", 60))
        if short_window <= 0 or long_window <= 0:
            raise ValueError("均線週期必須為正整數。")
        if short_window >= long_window:
            raise ValueError("short_window 必須小於 long_window。")
        return {
            "name": name,
            "type": strategy_type,
            "params": {
                "short_window": short_window,
                "long_window": long_window,
            },
        }

    if strategy_type == "dollar_cost_averaging":
        monthly_day = int(params.get("monthly_day", 5))
        monthly_amount = float(params.get("monthly_amount", 10_000))
        min_buy_unit = int(params.get("min_buy_unit", 1))
        if not 1 <= monthly_day <= 31:
            raise ValueError("monthly_day 必須介於 1 到 31。")
        if monthly_amount <= 0:
            raise ValueError("monthly_amount 必須大於 0。")
        if min_buy_unit < 1:
            raise ValueError("min_buy_unit 必須大於等於 1。")
        return {
            "name": name,
            "type": strategy_type,
            "params": {
                "monthly_day": monthly_day,
                "monthly_amount": monthly_amount,
                "min_buy_unit": min_buy_unit,
                "non_trading_day_policy": "next_trading_day",
                "buy_price_field": "close",
            },
        }

    raise ValueError(f"不支援的策略類型：{strategy_type}")


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

    # Keep names unique and stable.
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for preset in updated:
        name = str(preset.get("name", "")).strip() or _next_strategy_name(deduped, base="Strategy")
        if name in seen:
            name = _next_strategy_name(deduped, base=name)
        seen.add(name)
        deduped.append(
            {
                "name": name,
                "type": preset.get("type", ""),
                "params": preset.get("params", {}),
            }
        )
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


def _restore_defaults_and_env(clear_strategies: bool) -> None:
    root = get_project_root()
    config_path = root / "config.yaml"
    if config_path.exists():
        import yaml
        config = get_config().copy()
        config.pop("ui", None)
        config.pop("ai", None)
        config.pop("risk", None)
        config.pop("backtest", None)
        if clear_strategies:
            config.pop("strategies", None)
            config.pop("strategy", None)
        config.pop("secrets", None)
        config_path.write_text(
            yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )

def _save_config_and_env(
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
    strategies: list[dict[str, Any]],
    openai_key: str,
    anthropic_key: str,
    gemini_key: str,
) -> None:
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
    config["strategies"] = strategies
    config.pop("strategy", None)

    config_path.write_text(
        yaml.safe_dump(config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    _write_env(
        env_path,
        {
            "OPENAI_API_KEY": openai_key,
            "ANTHROPIC_API_KEY": anthropic_key,
            "GEMINI_API_KEY": gemini_key,
        },
    )


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


@st.dialog("恢復預設值確認")
def _confirm_restore_dialog() -> None:
    st.write("此操作將會恢復外觀、AI 模型、與風控參數的預設值。請問是否要一併清除所有已儲存的自訂策略？")
    if st.button("確定要清除已儲存的策略？", type="primary", use_container_width=True):
        _restore_defaults_and_env(clear_strategies=True)
        clear_config_cache()
        st.session_state["restore_success_msg"] = "已恢復預設值（含自訂策略）。"
        st.rerun()
    if st.button("不清除已儲存的策略", use_container_width=True):
        _restore_defaults_and_env(clear_strategies=False)
        clear_config_cache()
        st.session_state["restore_success_msg"] = "已恢復預設值（保留自訂策略）。"
        st.rerun()
    if st.button("取消", use_container_width=True):
        st.rerun()


if __name__ == "__main__":
    render()
