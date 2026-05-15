import { useState } from "react";

export interface Message {
  role: "user" | "assistant";
  content: string;
}

const MOCK_REPLY =
  "AI 串接尚未開放（這是 UI 預覽）。\n\n本訊息為模擬輸出，待 Phase 10-F-2 接上真實 LLM 後將改為串流逐字回應。";

const CHAR_DELAY_MS = 25; // 20-40ms 區間中位數

const GREETING: Message = {
  role: "assistant",
  content:
    "你好。可提問範例：2330 的 RSI 是多少？／回測 KD_Cross 在 2020 年的表現？",
};

export function useMockChat() {
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [isStreaming, setIsStreaming] = useState(false);

  function send(userText: string) {
    if (!userText.trim() || isStreaming) return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: userText },
      { role: "assistant", content: "" },
    ]);
    setIsStreaming(true);

    let i = 0;
    const timer = setInterval(() => {
      i += 1;
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: MOCK_REPLY.slice(0, i),
        };
        return next;
      });
      if (i >= MOCK_REPLY.length) {
        clearInterval(timer);
        setIsStreaming(false);
      }
    }, CHAR_DELAY_MS);
  }

  return { messages, isStreaming, send };
}
