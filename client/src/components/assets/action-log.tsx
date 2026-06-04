"use client";

import { ExternalLink } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { explorerTxUrl, explorerTokenUrl, explorerAddressUrl, type ChainBrand } from "@/lib/chains";

// Backend audit entries are flat: { sequence, timestamp, agent, action, details }.
// `content`/`consensus_timestamp` are tolerated for older/Hedera-shaped payloads.
interface LogEntry {
  sequence?: number;
  sequence_number?: number;
  timestamp?: string;
  consensus_timestamp?: string;
  created_at?: string;
  agent?: string;
  action?: string;
  details?: Record<string, unknown> | string;
  content?: {
    agent?: string;
    action?: string;
    details?: Record<string, unknown>;
    timestamp?: string;
  };
}

const agentColors: Record<string, string> = {
  lifecycle: "text-blue-400 bg-blue-400/10",
  compliance: "text-amber-400 bg-amber-400/10",
  reporting: "text-purple-400 bg-purple-400/10",
  chat: "text-emerald-400 bg-emerald-400/10",
};

const str = (v: unknown) => (typeof v === "string" && v && v !== "-" ? v : undefined);

/** Unwrap details: entries sometimes double-wrap as { details: {...} }. */
function unwrap(details: LogEntry["details"]): Record<string, unknown> {
  if (!details) return {};
  if (typeof details === "string") {
    try { return JSON.parse(details); } catch { return {}; }
  }
  if (typeof details === "object" && "details" in details && typeof details.details === "object") {
    return details.details as Record<string, unknown>;
  }
  return details as Record<string, unknown>;
}

/** Best on-chain explorer link for an entry: prefer a tx, then the token, then an account. */
function explorerLink(
  chain: ChainBrand | undefined,
  details: Record<string, unknown>,
): { label: string; url: string } | null {
  if (!chain?.explorer || !details) return null;

  const tx = str(details.tx) || str(details.tx_hash) || str(details.transaction_id);
  if (tx) {
    const url = explorerTxUrl(chain, tx);
    if (url) return { label: "tx", url };
  }
  const token = str(details.token_ref) || str(details.token_id);
  if (token) {
    const url = explorerTokenUrl(chain, token);
    if (url) return { label: "token", url };
  }
  const acct = str(details.account_id) || str(details.buyer) || str(details.to);
  if (acct) {
    const url = explorerAddressUrl(chain, acct);
    if (url) return { label: "account", url };
  }
  return null;
}

export default function ActionLog({ entries, chain }: { entries: LogEntry[]; chain?: ChainBrand }) {
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
          const timestamp = entry.content?.timestamp || entry.timestamp || entry.consensus_timestamp || entry.created_at || "";
          const details = unwrap(entry.content?.details ?? entry.details);
          const link = explorerLink(chain, details);

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
                {link && (
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[10px] text-primary/70 hover:text-primary transition-colors inline-flex items-center gap-0.5 mt-1"
                  >
                    <ExternalLink className="w-2.5 h-2.5" />
                    view {link.label}
                  </a>
                )}
              </div>
              <span className="text-[10px] text-muted-foreground/50 flex-shrink-0">
                {timestamp ? new Date(timestamp).toLocaleTimeString() : ""}
              </span>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
