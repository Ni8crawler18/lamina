"use client";

import ChatPanel from "@/components/ChatPanel";

export default function ChatPage() {
  return (
    <div className="h-screen flex flex-col">
      <div className="p-6 pb-0 border-b border-border">
        <h1 className="text-2xl font-bold">Chat Agent</h1>
        <p className="text-muted-foreground text-sm mb-4">
          Natural language interface for managing tokenized assets on Hedera
        </p>
      </div>
      <div className="flex-1">
        <ChatPanel />
      </div>
    </div>
  );
}
