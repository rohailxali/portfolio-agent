"use client";

import { useState, useRef, useEffect } from "react";
import { api } from "@/lib/api";
import type { ChatResponse, PendingAction } from "@/types";

interface ToolCall {
  tool: string;
  inputs: Record<string, unknown>;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  requiresConfirmation?: boolean;
  pendingAction?: PendingAction | null;
}

export default function AgentChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string, confirmPending = false, pendingAction?: PendingAction | null) {
    if (!text.trim() && !confirmPending) return;
    setLoading(true);

    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    try {
      const res: ChatResponse = await api.agent.chat({
        message: text,
        conversation_id: conversationId,
        confirm_pending: confirmPending || undefined,
        pending_action: pendingAction || undefined,
      });

      setConversationId(res.conversation_id);

      const assistantMsg: Message = {
        role: "assistant",
        content: res.reply,
        toolCalls: res.tool_calls,
        requiresConfirmation: res.requires_confirmation,
        pendingAction: res.pending_action,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  }

  async function confirm(pendingAction: PendingAction) {
    await send(`Confirmed. Proceed with ${pendingAction.tool_name}.`, true, pendingAction);
  }

  return (
    <div className="agent-chat">
      <div className="agent-chat__messages">
        {messages.length === 0 && (
          <p className="agent-chat__empty">
            Chat with your Portfolio Agent. Ask it to deploy, check site health, manage leads, and more.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`agent-chat__message agent-chat__message--${msg.role}`}>
            {msg.toolCalls && msg.toolCalls.length > 0 && (
              <div className="agent-chat__tool-calls">
                {msg.toolCalls.map((tc, j) => (
                  <span key={j} className="agent-chat__tool-badge">⚙ {tc.tool}</span>
                ))}
              </div>
            )}
            <pre className="agent-chat__content">{msg.content}</pre>
            {msg.requiresConfirmation && msg.pendingAction && (
              <div className="agent-chat__confirm-gate">
                <p>{msg.pendingAction.confirmation_message}</p>
                <div className="agent-chat__confirm-buttons">
                  <button
                    className="btn btn--danger"
                    onClick={() => confirm(msg.pendingAction!)}
                  >
                    Confirm
                  </button>
                  <button
                    className="btn btn--ghost"
                    onClick={() => setMessages((prev) => [...prev, { role: "user", content: "Cancelled." }])}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="agent-chat__message agent-chat__message--assistant">
            <span className="agent-chat__thinking">thinking…</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form
        className="agent-chat__input-row"
        onSubmit={(e) => { e.preventDefault(); send(input); }}
      >
        <input
          className="agent-chat__input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message the agent…"
          disabled={loading}
          autoFocus
        />
        <button className="btn btn--primary" type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
        <button
          className="btn btn--ghost"
          type="button"
          onClick={() => { setMessages([]); setConversationId(undefined); }}
        >
          New
        </button>
      </form>
    </div>
  );
}
