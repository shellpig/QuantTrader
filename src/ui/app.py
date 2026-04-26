"""Streamlit entrypoint for QuantTrader UI."""

from __future__ import annotations

import streamlit as st

from src.core.config import get_config
from src.ui.pages import ai_chat, backtest, data_management, settings


def main() -> None:
    st.set_page_config(page_title="QuantTrader", page_icon="📊", layout="wide")

    config = get_config()
    ai_section = config.get("ai", {}) if isinstance(config, dict) else {}
    ai_enabled = bool(ai_section.get("enabled", True))

    st.sidebar.title("QuantTrader")
    st.sidebar.caption("台股量化研究工具")
    if ai_enabled:
        st.sidebar.success("AI 功能：啟用")
    else:
        st.sidebar.info("AI 功能：停用")

    page_name = st.sidebar.radio(
        "功能頁面",
        options=["資料管理", "回測", "AI 問答", "設定"],
        index=0,
    )

    if page_name == "資料管理":
        data_management.render()
    elif page_name == "回測":
        backtest.render()
    elif page_name == "AI 問答":
        ai_chat.render()
    else:
        settings.render()


if __name__ == "__main__":
    main()

