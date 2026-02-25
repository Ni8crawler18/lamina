"use client";

import { useState, useRef, useEffect } from "react";
import { sendChat } from "@/lib/api";

interface Action {
  tool: string;
  input: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  status: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  actions?: Action[];
  loading?: boolean;
}

const SUGGESTIONS = [
  "Tokenize a $10M 5-year US Treasury bond",
  "List all assets",
  "Show holders for asset 1",
  "Distribute coupon for asset 1",
  "Generate compliance report",
];

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "I'm Lamina, your RWA lifecycle agent on Hedera. I can tokenize assets, manage compliance, distribute coupons, and generate reports. What would you like to do?",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (text?: string) => {
    const message = text || input;
    if (!message.trim() || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "", loading: true }]);
    setLoading(true);

    try {
      const result = await sendChat(message);
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: result.response,
          actions: result.actions_taken,
        };
        return next;
      });
    } catch (err) {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: `Error: ${err instanceof Error ? err.message : "Something went wrong"}`,
        };
        return next;
      });
    } finally {
      setLoading(false);
    }
  };

  const showSuggestions = messages.length <= 2;

  return (
    <div className="flex flex-col h-full">
      {/* Messages — anchored to bottom */}
      <div className="flex-1 overflow-y-auto" ref={scrollRef}>
        <div className={`flex flex-col min-h-full px-6 py-6 ${showSuggestions ? "justify-end" : ""}`}>
          <div className="max-w-2xl mx-auto w-full space-y-5">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className="max-w-[85%]">
                  {msg.role === "assistant" && (
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-5 h-5 rounded-md bg-primary/20 flex items-center justify-center">
                        <svg className="w-3 h-3 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                      </div>
                      <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Lamina</span>
                    </div>
                  )}
                  <div className={`rounded-xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-card/60 border border-border/50"
                  }`}>
                    {msg.loading ? (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <div className="w-3.5 h-3.5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                        Processing...
                      </div>
                    ) : (
                      <>
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                        {msg.actions && msg.actions.length > 0 && (
                          <div className="mt-3 space-y-1.5">
                            {msg.actions.map((action, j) => (
                              <div key={j} className="rounded-lg bg-background/50 border border-border/30 px-3 py-2">
                                <div className="flex items-center gap-2">
                                  <span className={`w-1.5 h-1.5 rounded-full ${
                                    action.status === "success" ? "bg-emerald-400" : "bg-red-400"
                                  }`} />
                                  <span className="font-mono text-[11px] text-muted-foreground">{action.tool}</span>
                                </div>
                                {action.result && (
                                  <pre className="font-mono text-[10px] text-muted-foreground/60 mt-1 overflow-hidden text-ellipsis max-h-16 leading-tight">
                                    {JSON.stringify(action.result, null, 2).slice(0, 200)}
                                  </pre>
                                )}
                                {action.error && (
                                  <p className="text-[10px] text-red-400 mt-1">{action.error}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Suggestions */}
      {showSuggestions && (
        <div className="px-6 pb-3">
          <div className="flex flex-wrap gap-1.5 max-w-2xl mx-auto justify-center">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSend(s)}
                className="text-[11px] px-3 py-1.5 rounded-full border border-border/50 text-muted-foreground hover:text-foreground hover:border-primary/30 hover:bg-primary/5 transition-all duration-150"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 border-t border-border/30">
        <form
          onSubmit={(e) => { e.preventDefault(); handleSend(); }}
          className="flex gap-2 max-w-2xl mx-auto"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message Lamina..."
            disabled={loading}
            className="flex-1 bg-card/30 border border-border/50 rounded-xl px-4 py-2.5 text-sm placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/40 transition-colors disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-medium hover:bg-primary/90 transition-colors disabled:opacity-30"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
