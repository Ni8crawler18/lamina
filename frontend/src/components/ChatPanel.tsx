"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
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
  "Tokenize a $10M 5-year US Treasury bond, US accredited investors only",
  "List all assets",
  "Show holders for asset 1",
  "Distribute coupon for asset 1",
  "Generate compliance report for asset 1",
];

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm Lamina, your autonomous RWA lifecycle agent on Hedera. I can tokenize assets, manage compliance, distribute coupons, and more. What would you like to do?",
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

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)]">
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4 max-w-3xl mx-auto">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted"
                }`}
              >
                {msg.loading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
                    Processing...
                  </div>
                ) : (
                  <>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                    {msg.actions && msg.actions.length > 0 && (
                      <div className="mt-3 space-y-2">
                        {msg.actions.map((action, j) => (
                          <Card key={j} className="p-2 bg-background/50">
                            <div className="flex items-center gap-2">
                              <Badge
                                variant="outline"
                                className={
                                  action.status === "success"
                                    ? "bg-green-500/10 text-green-500 border-green-500/20"
                                    : "bg-red-500/10 text-red-500 border-red-500/20"
                                }
                              >
                                {action.status}
                              </Badge>
                              <span className="text-xs font-mono">{action.tool}</span>
                            </div>
                            {action.result && (
                              <pre className="text-xs text-muted-foreground mt-1 overflow-hidden text-ellipsis max-h-20">
                                {JSON.stringify(action.result, null, 2).slice(0, 200)}
                              </pre>
                            )}
                            {action.error && (
                              <p className="text-xs text-red-500 mt-1">{action.error}</p>
                            )}
                          </Card>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Suggestions */}
      {messages.length <= 2 && (
        <div className="px-4 pb-2">
          <div className="flex flex-wrap gap-2 max-w-3xl mx-auto">
            {SUGGESTIONS.map((s, i) => (
              <button
                key={i}
                onClick={() => handleSend(s)}
                className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
              >
                {s.length > 50 ? s.slice(0, 50) + "..." : s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-border">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2 max-w-3xl mx-auto"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder='Try "Tokenize a $10M 5-year US Treasury bond"'
            disabled={loading}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !input.trim()}>
            {loading ? "Sending..." : "Send"}
          </Button>
        </form>
      </div>
    </div>
  );
}
