"use client";

import { ExternalLink } from "lucide-react";
import type { ChainBrand } from "@/lib/chains";

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

/** Best on-chain explorer link for an entry: prefer a tx, then the token, then an account. */
function explorerLink(
  chain: ChainBrand | undefined,
  details: Record<string, unknown>,
): { label: string; url: string } | null {
  if (!chain?.explorer || !details) return null;
  const evm = chain.family !== "hedera";
  const str = (v: unknown) => (typeof v === "string" && v && v !== "-" ? v : undefined);

  const tx = str(details.tx) || str(details.tx_hash) || str(details.transaction_id);
  if (tx) {
    const h = evm ? (tx.startsWith("0x") ? tx : `0x${tx}`) : tx;
    return { label: "transaction", url: evm ? `${chain.explorer}/tx/${h}` : `${chain.explorer}/transaction/${tx}` };
  }
  const token = str(details.token_ref) || str(details.token_id);
  if (token) return { label: "token", url: evm ? `${chain.explorer}/address/${token}` : `${chain.explorer}/token/${token}` };
  const acct = str(details.account_id) || str(details.buyer) || str(details.to);
  if (acct) return { label: "account", url: evm ? `${chain.explorer}/address/${acct}` : `${chain.explorer}/account/${acct}` };
  return null;
}

export default function AuditTimeline({
  entries,
  topicId,
  chain,
}: {
  entries: LogEntry[];
  topicId?: string;
  chain?: ChainBrand;
}) {
  const isHedera = chain?.family === "hedera";
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
          const entryTopicId = entry.topic_id || topicId;
          const link = explorerLink(chain, details as Record<string, unknown>);

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

                  {link ? (
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary/70 hover:text-primary transition-colors inline-flex items-center gap-0.5"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      view {link.label}
                    </a>
                  ) : isHedera && entryTopicId ? (
                    <a
                      href={`${chain?.explorer || "https://hashscan.io/testnet"}/topic/${entryTopicId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary/70 hover:text-primary transition-colors inline-flex items-center gap-0.5"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      audit topic
                    </a>
                  ) : null}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
