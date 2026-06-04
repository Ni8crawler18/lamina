"use client";

import { useState, useEffect } from "react";
import { DollarSign, Clock, TrendingUp, FileText, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { explorerTxUrl, type ChainBrand } from "@/lib/chains";

interface ScheduledEvent {
  id: number;
  asset_id: number;
  event_type: string;
  scheduled_at: string;
  executed_at: string | null;
  status: string;
  tx_hash: string | null;
  details: string | null;
}

const eventConfig: Record<string, { icon: typeof DollarSign; dotColor: string; color: string; bgColor: string; label: string }> = {
  coupon_payment: { icon: DollarSign, dotColor: "bg-blue-400", color: "text-blue-400", bgColor: "bg-blue-400/10", label: "Coupon Payment" },
  maturity: { icon: Clock, dotColor: "bg-red-400", color: "text-red-400", bgColor: "bg-red-400/10", label: "Maturity" },
  nav_update: { icon: TrendingUp, dotColor: "bg-emerald-400", color: "text-emerald-400", bgColor: "bg-emerald-400/10", label: "NAV Update" },
  report: { icon: FileText, dotColor: "bg-purple-400", color: "text-purple-400", bgColor: "bg-purple-400/10", label: "Report" },
};

const statusBadge: Record<string, string> = {
  completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  pending: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  cancelled: "bg-red-500/10 text-red-400 border-red-500/20",
  failed: "bg-red-500/10 text-red-400 border-red-500/20",
};

function formatCountdown(scheduledAt: string): { text: string; overdue: boolean } {
  const diff = new Date(scheduledAt).getTime() - Date.now();
  if (diff <= 0) return { text: "overdue", overdue: true };

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));

  if (days > 0) return { text: `in ${days}d ${hours}h`, overdue: false };
  if (hours > 0) return { text: `in ${hours}h ${minutes}m`, overdue: false };
  return { text: `in ${minutes}m`, overdue: false };
}

export default function EventTimeline({ events, chain }: { events: ScheduledEvent[]; chain?: ChainBrand }) {
  const [, setTick] = useState(0);

  // Tick every 60s to update countdowns
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 60000);
    return () => clearInterval(interval);
  }, []);

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/20 p-12 text-center">
        <p className="text-sm text-muted-foreground">No scheduled events</p>
      </div>
    );
  }

  // Sort: pending (soonest first) at top, then completed (newest first)
  const sorted = [...events].sort((a, b) => {
    if (a.status === "pending" && b.status !== "pending") return -1;
    if (a.status !== "pending" && b.status === "pending") return 1;
    if (a.status === "pending" && b.status === "pending") {
      return new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime();
    }
    // Both non-pending: newest first
    const aTime = a.executed_at || a.scheduled_at;
    const bTime = b.executed_at || b.scheduled_at;
    return new Date(bTime).getTime() - new Date(aTime).getTime();
  });

  return (
    <div className="relative">
      {/* Timeline line */}
      <div className="absolute left-[19px] top-0 bottom-0 w-px bg-border/30" />

      <div className="space-y-1">
        {sorted.map((event) => {
          const config = eventConfig[event.event_type] || eventConfig.report;
          const Icon = config.icon;
          const isPending = event.status === "pending";
          const countdown = isPending ? formatCountdown(event.scheduled_at) : null;

          let parsedDetails: Record<string, unknown> = {};
          if (event.details) {
            try { parsedDetails = JSON.parse(event.details); } catch { /* skip */ }
          }

          return (
            <div
              key={event.id}
              className="relative flex gap-4 px-2 py-3 rounded-lg hover:bg-card/30 transition-colors group"
            >
              {/* Timeline dot */}
              <div className="relative z-10 flex-shrink-0 mt-1">
                <div className={`w-2.5 h-2.5 rounded-full ${config.dotColor} ring-4 ring-background`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className={`inline-flex items-center gap-1 text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${config.bgColor} ${config.color}`}>
                    <Icon className="w-3 h-3" />
                    {config.label}
                  </span>
                  <Badge variant="outline" className={`text-[10px] ${statusBadge[event.status] || statusBadge.pending}`}>
                    {event.status}
                  </Badge>
                  {isPending && countdown && (
                    <span className={`text-xs font-mono font-medium ${countdown.overdue ? "text-red-400" : "text-amber-400"}`}>
                      {countdown.text}
                    </span>
                  )}
                </div>

                {Object.keys(parsedDetails).length > 0 && (
                  <p className="font-mono text-[11px] text-muted-foreground/60 truncate max-w-lg">
                    {JSON.stringify(parsedDetails).slice(0, 120)}
                  </p>
                )}

                <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                  <span className="text-[10px] text-muted-foreground/50">
                    {isPending
                      ? `Scheduled: ${new Date(event.scheduled_at).toLocaleString()}`
                      : `Executed: ${event.executed_at ? new Date(event.executed_at).toLocaleString() : new Date(event.scheduled_at).toLocaleString()}`}
                  </span>

                  {event.tx_hash && explorerTxUrl(chain, event.tx_hash) && (
                    <a
                      href={explorerTxUrl(chain, event.tx_hash)!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] text-primary/70 hover:text-primary transition-colors inline-flex items-center gap-0.5 opacity-0 group-hover:opacity-100"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      view tx
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
