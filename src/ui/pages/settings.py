"""Settings page."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import yaml

from src.core.config import clear_config_cache, get_config, get_project_root


def render() -> None:
    st.title("設定")
    st.caption("調整 AI、回測與風控參數，並儲存為預設。")

    config = get_config()
    ai = config.get("ai", {}) if isinstance(config, dict) else {}
    risk = config.get("risk", {}) if isinstance(config, dict) else {}
    backtest = config.get("backtest", {}) if isinstance(config, dict) else {}
    secrets = config.get("secrets", {}) if isinstance(config, dict) else {}

    st.subheader("AI 設定")
    ai_enabled = st.toggle("啟用 AI 問答（ai.enabled）", value=bool(ai.get("enabled", True)))
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

    if st.button("儲存為預設", type="primary"):
        try:
            _save_config_and_env(
                ai_enabled=ai_enabled,
                provider=provider,
                model=model,
                max_daily_loss_pct=max_daily_loss_pct,
                max_position_pct=max_position_pct,
                max_drawdown_warning_pct=max_drawdown_warning_pct,
                initial_capital=initial_capital,
                openai_key=openai_key,
                anthropic_key=anthropic_key,
                gemini_key=gemini_key,
            )
            clear_config_cache()
            st.success("設定已儲存。")
            st.info("若要立即反映在頁面切換邏輯，可重新整理頁面。")
        except Exception as exc:  # noqa: BLE001
            st.error(f"儲存失敗：{exc}")

    st.subheader("當前設定快照")
    st.json(
        {
            "ai": {"enabled": ai_enabled, "provider": provider, "model": model},
            "risk": {
                "max_daily_loss_pct": max_daily_loss_pct,
                "max_position_pct": max_position_pct,
                "max_drawdown_warning_pct": max_drawdown_warning_pct,
            },
            "backtest": {"initial_capital": initial_capital},
        },
        expanded=False,
    )


def _save_config_and_env(
    *,
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
    root = get_project_root()
    config_path = root / "config.yaml"
    env_path = root / ".env"

    config = get_config().copy()
    config.pop("secrets", None)
    if "ai" not in config or not isinstance(config["ai"], dict):
        config["ai"] = {}
    if "risk" not in config or not isinstance(config["risk"], dict):
        config["risk"] = {}
    if "backtest" not in config or not isinstance(config["backtest"], dict):
        config["backtest"] = {}

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


if __name__ == "__main__":
    render()
