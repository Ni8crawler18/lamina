"use client";

import { useState, useEffect } from "react";
import { getAssets, getAuditLog } from "@/lib/api";
import AuditTimeline from "@/components/history/audit-timeline";

interface Asset {
  id: number;
  name: string;
  symbol: string;
}

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

export default function HistoryPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [allEntries, setAllEntries] = useState<LogEntry[]>([]);
  const [selectedAssetId, setSelectedAssetId] = useState<number | null>(null);
  const [agentFilter, setAgentFilter] = useState("all");
  const [topicId, setTopicId] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAssets();
        setAssets(data);

        // Load all audit logs
        const entries: LogEntry[] = [];
        for (const asset of data) {
          try {
            const audit = await getAuditLog(asset.id);
            const hcs = (audit.hcs_messages || []).map((m: LogEntry) => ({ ...m, topic_id: audit.topic_id }));
            const local = audit.local_log || [];
            entries.push(...hcs, ...local);
            if (audit.topic_id && !topicId) setTopicId(audit.topic_id);
          } catch {
            // Skip
          }
        }
        // Sort newest first
        entries.sort((a, b) => {
          const tA = a.content?.timestamp || a.consensus_timestamp || a.created_at || "";
          const tB = b.content?.timestamp || b.consensus_timestamp || b.created_at || "";
          return new Date(tB).getTime() - new Date(tA).getTime();
        });
        setAllEntries(entries);
      } catch (err) {
        console.error("Failed to load:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = allEntries.filter((entry) => {
    const agent = entry.content?.agent || entry.agent || "unknown";
    if (agentFilter !== "all" && agent !== agentFilter) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight">Audit History</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Immutable action log — verified on Hedera Consensus Service
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <select
          value={selectedAssetId ?? "all"}
          onChange={(e) => setSelectedAssetId(e.target.value === "all" ? null : Number(e.target.value))}
          className="bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        >
          <option value="all">All Assets</option>
          {assets.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>

        <div className="flex gap-1.5">
          {["all", "lifecycle", "compliance", "reporting", "chat"].map((agent) => (
            <button
              key={agent}
              onClick={() => setAgentFilter(agent)}
              className={`px-2.5 py-1 text-[11px] rounded-md border transition-all ${
                agentFilter === agent
                  ? "border-primary/30 bg-primary/10 text-foreground"
                  : "border-border/50 text-muted-foreground hover:text-foreground"
              }`}
            >
              {agent === "all" ? "All" : agent}
            </button>
          ))}
        </div>

        <span className="text-xs text-muted-foreground ml-auto">
          {filtered.length} entries
        </span>
      </div>

      <AuditTimeline entries={filtered} topicId={topicId} />
    </div>
  );
}
