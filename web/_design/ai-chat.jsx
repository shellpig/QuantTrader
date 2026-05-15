/* AI 問答 page — SSE-streamed chat. */

const { useState: useStateAi } = React;

const INITIAL_MESSAGES = [
  { role: "assistant", content: "你好。可提問範例：2330 的 RSI 是多少？／回測 KD_Cross 在 2020 年的表現？" },
  { role: "user",      content: "2330 的 RSI 是多少？" },
  { role: "assistant", content: "2330（台積電）在 2025-04-29 收盤的 RSI_14 為 **62.4**，落於中性偏多區間（30–70）。\n\n參考數據：\n- RSI_5：68.1\n- RSI_14：62.4\n- RSI_28：55.8\n\nRSI 為動能指標，>70 通常視為超買、<30 視為超賣。RSI_14 緩升表示動能仍偏多但未過熱。" },
];

const DISCLAIMER = "本工具提供的分析僅供研究參考，並非投資建議。投資人需自行評估風險並承擔後果。";

function AIChatPage() {
  const [accepted, setAccepted] = useStateAi(true);
  const [messages, setMessages] = useStateAi(INITIAL_MESSAGES);
  const [draft, setDraft] = useStateAi("");

  if (!accepted) {
    return (
      <>
        <Header title="AI 問答" caption="使用前請先閱讀免責聲明。"/>
        <Card style={{ maxWidth: 640 }}>
          <SectionHeader title="免責聲明"/>
          <p style={{ fontSize: 13, color: "hsl(var(--muted-foreground))", lineHeight: 1.6 }}>{DISCLAIMER}</p>
          <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
            <Button variant="primary" onClick={() => setAccepted(true)}>我了解</Button>
          </div>
        </Card>
      </>
    );
  }

  function send() {
    if (!draft.trim()) return;
    setMessages([...messages,
      { role: "user", content: draft },
      { role: "assistant", content: "分析中...（這是 UI 預覽，未串接真實 LLM）" },
    ]);
    setDraft("");
  }

  return (
    <>
      <Header title="AI 問答" caption="可提問範例：2330 的 RSI 是多少？回測 KD_Cross 在 2020 的表現？">
        <Chip variant="rise"><Icon name="check" size={12}/> AI · 已啟用</Chip>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "hsl(var(--muted-foreground))" }}>anthropic · claude-sonnet-4-6</span>
      </Header>
      <Card style={{ padding: 0, display: "flex", flexDirection: "column", height: "calc(100vh - 220px)" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
          {messages.map((m, i) => <MessageBubble key={i} role={m.role} content={m.content}/>)}
        </div>
        <div style={{ borderTop: "1px solid hsl(var(--border))", padding: 12, display: "flex", gap: 8 }}>
          <input
            type="text"
            placeholder="輸入你的問題..."
            value={draft}
            onChange={e => setDraft(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") send(); }}
            style={{
              flex: 1,
              fontFamily: "var(--font-sans)",
              fontSize: 14,
              padding: "10px 14px",
              background: "hsl(var(--background))",
              color: "hsl(var(--foreground))",
              border: "1px solid hsl(var(--border))",
              borderRadius: 8,
              outline: "none",
            }}
          />
          <Button variant="primary" icon="send" onClick={send}>送出</Button>
        </div>
      </Card>
      <div style={{ marginTop: 10, fontSize: 11, color: "hsl(var(--muted-foreground))", fontFamily: "var(--font-mono)" }}>
        {DISCLAIMER}
      </div>
    </>
  );
}

function MessageBubble({ role, content }) {
  const isUser = role === "user";
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start", gap: 4 }}>
      <div style={{ fontSize: 10, color: "hsl(var(--muted-foreground))", letterSpacing: "0.06em", textTransform: "uppercase" }}>
        {isUser ? "你" : "AI"}
      </div>
      <div style={{
        maxWidth: "78%",
        padding: "10px 14px",
        background: isUser ? "hsl(var(--primary) / 0.12)" : "hsl(var(--card))",
        border: isUser ? "1px solid hsl(var(--primary) / 0.3)" : "1px solid hsl(var(--border))",
        color: "hsl(var(--foreground))",
        borderRadius: 10,
        fontSize: 14,
        lineHeight: 1.6,
        whiteSpace: "pre-wrap",
      }}>
        {content.split("\n").map((line, i) => <div key={i}>{line || "\u00A0"}</div>)}
      </div>
    </div>
  );
}

Object.assign(window, { AIChatPage });
