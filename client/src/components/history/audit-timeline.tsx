"use client";

import { ExternalLink } from "lucide-react";

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
  topic_id?: string;
}

const agentColors: Record<string, string> = {
  lifecycle: "bg-blue-400",
  compliance: "bg-amber-400",
  reporting: "bg-purple-400",
  chat: "bg-emerald-400",
};

const agentBadgeColors: Record<string, string> = {
  lifecycle: "text-blue-400 bg-blue-400/10",
  compliance: "text-amber-400 bg-amber-400/10",
  reporting: "text-purple-400 bg-purple-400/10",
  chat: "text-emerald-400 bg-emerald-400/10",
};

export default function AuditTimeline({
  entries,
  topicId,
}: {
  entries: LogEntry[];
  topicId?: string;
}) {
  if (entries.length === 0) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/20 p-12 text-center">
        <p className="text-sm text-muted-foreground">No audit entries yet</p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-[19px] top-0 bottom-0 w-px bg-border/30" />

      <div className="space-y-1">
        {entries.map((entry, i) => {
          const agent = entry.content?.agent || entry.agent || "unknown";
          const action = entry.content?.action || entry.action || "unknown";
          const timestamp = entry.content?.timestamp || entry.consensus_timestamp || entry.created_at || "";
          const details = entry.content?.details || (entry.details ? (() => { try { return JSON.parse(entry.details as string); } catch { return {}; } })() : {});
          const isHCS = entry.sequence_number != null;
          const entryTopicId = entry.topic_id || topicId;

          return (
            <div key={i} className="relative flex gap-4 px-2 py-3 rounded-lg hover:bg-card/30 transition-colors group">
              {/* Timeline dot */}
              <div className="relative z-10 flex-shrink-0 mt-1">
                <div className={`w-2.5 h-2.5 rounded-full ${agentColors[agent] || "bg-muted-foreground"} ring-4 ring-background`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${agentBadgeColors[agent] || "text-muted-foreground bg-muted"}`}>
                    {agent}
                  </span>
                  <span className="text-sm">{action.replace(/_/g, " ")}</span>
                </div>

                {Object.keys(details).length > 0 && (
                  <p className="font-mono text-[11px] text-muted-foreground/60 truncate max-w-lg">
                    {JSON.stringify(details).slice(0, 120)}
                  </p>
                )}

                <div className="flex items-center gap-3 mt-1.5">
                  <span className="text-[10px] text-muted-foreground/50">
                    {timestamp ? new Date(timestamp).toLocaleString() : ""}
                  </span>

                  {isHCS && (
                    <span className="inline-flex items-center gap-1 text-[10px] text-primary/70 bg-primary/5 px-1.5 py-0.5 rounded">
                      <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      HCS #{entry.sequence_number}
                    </span>
                  )}

                  {isHCS && entryTopicId && (
                    <a
                      href={`https://hashscan.io/testnet/topic/${entryTopicId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-muted-foreground/40 hover:text-primary/70 transition-colors opacity-0 group-hover:opacity-100 inline-flex items-center gap-0.5"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      HashScan
                    </a>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
