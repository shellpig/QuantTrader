"""AI chat page."""

from __future__ import annotations

import streamlit as st

from src.ai.advisor import AIAdvisor, DISCLAIMER
from src.core.config import get_config


def render() -> None:
    st.title("AI 問答")

    config = get_config()
    ai_section = config.get("ai", {}) if isinstance(config, dict) else {}
    ai_enabled = bool(ai_section.get("enabled", True))

    if not ai_enabled:
        st.info("AI 功能已關閉（ai.enabled=false）。請到「設定」頁開啟。")
        return

    if not st.session_state.get("ai_disclaimer_accepted", False):
        st.warning("使用前請先閱讀免責聲明。")
        st.markdown(DISCLAIMER)
        if st.button("我了解", type="primary"):
            st.session_state["ai_disclaimer_accepted"] = True
            st.rerun()
        return

    st.caption("可提問範例：2330 的 RSI 是多少？")

    if "ai_chat_messages" not in st.session_state:
        st.session_state["ai_chat_messages"] = []

    for message in st.session_state["ai_chat_messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("輸入你的問題...")
    if not prompt:
        return

    st.session_state["ai_chat_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("分析中..."):
            try:
                advisor = AIAdvisor()
                answer = advisor.ask(prompt)
            except Exception as exc:  # noqa: BLE001
                answer = f"AI 問答失敗：{exc}"
            st.markdown(answer)

    st.session_state["ai_chat_messages"].append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    render()
