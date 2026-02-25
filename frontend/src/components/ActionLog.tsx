"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";

interface LogEntry {
  sequence_number?: number;
  consensus_timestamp?: string;
  content?: {
    agent?: string;
    action?: string;
    details?: Record<string, unknown>;
    timestamp?: string;
  };
  // Local log fields
  action?: string;
  agent?: string;
  details?: string;
  created_at?: string;
}

const agentColors: Record<string, string> = {
  lifecycle: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  compliance: "bg-amber-500/10 text-amber-500 border-amber-500/20",
  reporting: "bg-purple-500/10 text-purple-500 border-purple-500/20",
  chat: "bg-green-500/10 text-green-500 border-green-500/20",
};

export default function ActionLog({ entries }: { entries: LogEntry[] }) {
  if (!entries || entries.length === 0) {
    return (
      <div className="text-sm text-muted-foreground text-center py-8">
        No actions logged yet
      </div>
    );
  }

  return (
    <ScrollArea className="h-[400px]">
      <div className="space-y-2">
        {entries.map((entry, i) => {
          const agent = entry.content?.agent || entry.agent || "unknown";
          const action = entry.content?.action || entry.action || "unknown";
          const timestamp = entry.content?.timestamp || entry.consensus_timestamp || entry.created_at || "";
          const details = entry.content?.details || (entry.details ? JSON.parse(entry.details) : {});

          return (
            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50 text-sm">
              <div className="flex-shrink-0 mt-0.5">
                <Badge variant="outline" className={agentColors[agent] || "bg-muted text-muted-foreground"}>
                  {agent}
                </Badge>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">{action.replace(/_/g, " ")}</p>
                {Object.keys(details).length > 0 && (
                  <p className="text-xs text-muted-foreground mt-1 truncate">
                    {JSON.stringify(details).slice(0, 120)}
                  </p>
                )}
              </div>
              <div className="flex-shrink-0 text-xs text-muted-foreground">
                {timestamp ? new Date(timestamp).toLocaleTimeString() : ""}
                {entry.sequence_number != null && (
                  <span className="ml-1 font-mono">#{entry.sequence_number}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
