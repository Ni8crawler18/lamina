"use client";

import { ScrollArea } from "@/components/ui/scroll-area";

interface LogEntry {
  sequence_number?: number;
  consensus_timestamp?: string;
  content?: {
    agent?: string;
    action?: string;
    details?: Record<string, unknown>;
    timestamp?: string;
  };
  action?: string;
  agent?: string;
  details?: string;
  created_at?: string;
}

const agentColors: Record<string, string> = {
  lifecycle: "text-blue-400 bg-blue-400/10",
  compliance: "text-amber-400 bg-amber-400/10",
  reporting: "text-purple-400 bg-purple-400/10",
  chat: "text-emerald-400 bg-emerald-400/10",
};

export default function ActionLog({ entries }: { entries: LogEntry[] }) {
  if (!entries || entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        No actions logged yet
      </p>
    );
  }

  return (
    <ScrollArea className="h-[420px]">
      <div className="space-y-px">
        {entries.map((entry, i) => {
          const agent = entry.content?.agent || entry.agent || "unknown";
          const action = entry.content?.action || entry.action || "unknown";
          const timestamp = entry.content?.timestamp || entry.consensus_timestamp || entry.created_at || "";
          const details = entry.content?.details || (entry.details ? JSON.parse(entry.details) : {});

          return (
            <div key={i} className="flex items-start gap-3 px-4 py-3 rounded-lg hover:bg-card/50 transition-colors">
              <span className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${agentColors[agent] || "text-muted-foreground bg-muted"}`}>
                {agent}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{action.replace(/_/g, " ")}</p>
                {Object.keys(details).length > 0 && (
                  <p className="font-mono text-[11px] text-muted-foreground/60 mt-0.5 truncate">
                    {JSON.stringify(details).slice(0, 100)}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {entry.sequence_number != null && (
                  <span className="font-mono text-[10px] text-primary/60">#{entry.sequence_number}</span>
                )}
                <span className="text-[10px] text-muted-foreground/50">
                  {timestamp ? new Date(timestamp).toLocaleTimeString() : ""}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
