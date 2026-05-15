"use client";

import { useState, useEffect, useRef } from "react";
import { DisclaimerGate, isDisclaimerAccepted } from "./disclaimer-gate";
import { MessageBubble } from "./message-bubble";
import { ChatInput } from "./chat-input";
import { useMockChat } from "@/hooks/use-mock-chat";

export function ChatPageClient() {
  const [accepted, setAccepted] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { messages, isStreaming, send } = useMockChat();

  // Read localStorage after mount (avoid SSR mismatch)
  useEffect(() => {
    setAccepted(isDisclaimerAccepted());
  }, []);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // While checking localStorage, render nothing to avoid flash
  if (accepted === null) return null;

  if (!accepted) {
    return (
      <div className="flex h-full flex-col" data-testid="chat-page">
        <DisclaimerGate onAccept={() => setAccepted(true)} />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col" data-testid="chat-page">
      {/* Message list */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        {messages.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <ChatInput onSend={send} disabled={isStreaming} />
    </div>
  );
}
