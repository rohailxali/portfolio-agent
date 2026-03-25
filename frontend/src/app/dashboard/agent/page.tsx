"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { api } from "../../../lib/api";
import type { ChatResponse, PendingAction } from "../../../types";
import styles from "./agent.module.css";

interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
  toolCalls?: { tool: string; inputs: Record<string, unknown> }[];
}

export default function AgentPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "system",
      content: "Agent ready. Type a command or question.",
    },
  ]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(text: string, confirmPending = false) {
    if (!text.trim() && !confirmPending) return;

    const userMsg: ChatMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: ChatResponse = await api.agent.chat({
        message: text,
        conversation_id: conversationId ?? undefined,
        confirm_pending: confirmPending,
        pending_action: confirmPending ? pendingAction : undefined,
      });

      setConversationId(res.conversation_id);

      const assistantMsg: ChatMessage = {
        role: "assistant",
        content: res.reply,
        toolCalls: res.tool_calls,
      };
      setMessages((prev) => [...prev, assistantMsg]);

      if (res.requires_confirmation && res.pending_action) {
        setPendingAction(res.pending_action);
      } else {
        setPendingAction(null);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "system", content: `Error: ${err}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  }

  function handleConfirm() {
    if (!pendingAction) return;
    sendMessage(`Confirmed. Proceed with ${pendingAction.tool_name}.`, true);
    setPendingAction(null);
  }

  function handleDeny() {
    setPendingAction(null);
    setMessages((prev) => [
      ...prev,
      { role: "system", content: "Action cancelled." },
    ]);
  }

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <h1 className={styles.title}>AGENT TERMINAL</h1>
        {conversationId && (
          <span className={styles.convId}>
            SESSION {conversationId.slice(0, 8).toUpperCase()}
          </span>
        )}
      </header>

      <div className={styles.feed}>
        {messages.map((msg, i) => (
          <div key={i} className={`${styles.msg} ${styles[`msg_${msg.role}`]}`}>
            <span className={styles.msgRole}>
              {msg.role === "user"
                ? "YOU"
                : msg.role === "assistant"
                ? "AGENT"
                : "SYS"}
            </span>
            <div className={styles.msgBody}>
              <p>{msg.content}</p>
              {msg.toolCalls && msg.toolCalls.length > 0 && (
                <div className={styles.toolCalls}>
                  {msg.toolCalls.map((tc, j) => (
                    <span key={j} className={styles.toolChip}>
                      ⚙ {tc.tool}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className={`${styles.msg} ${styles.msg_assistant}`}>
            <span className={styles.msgRole}>AGENT</span>
            <div className={styles.msgBody}>
              <span className={styles.thinking}>▌</span>
            </div>
          </div>
        )}

        {pendingAction && (
          <div className={styles.confirmation}>
            <p className={styles.confirmLabel}>⚠ CONFIRMATION REQUIRED</p>
            <p className={styles.confirmText}>{pendingAction.confirmation_message}</p>
            <p className={styles.confirmTool}>
              Tool: <strong>{pendingAction.tool_name}</strong>
            </p>
            <div className={styles.confirmBtns}>
              <button className={styles.btnConfirm} onClick={handleConfirm}>
                CONFIRM
              </button>
              <button className={styles.btnDeny} onClick={handleDeny}>
                CANCEL
              </button>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className={styles.inputArea}>
        <span className={styles.prompt}>›</span>
        <textarea
          className={styles.input}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="e.g. check site health · deploy main · classify new leads"
          rows={1}
          disabled={loading}
        />
        <button
          className={styles.sendBtn}
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          SEND
        </button>
      </div>
    </div>
  );
}