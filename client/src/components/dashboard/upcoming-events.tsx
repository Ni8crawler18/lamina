"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { DollarSign, Clock, TrendingUp, FileText } from "lucide-react";
import { getUpcomingEvents } from "@/lib/api";

interface UpcomingEvent {
  id: number;
  asset_id: number;
  event_type: string;
  scheduled_at: string;
  status: string;
  asset_name: string;
  asset_symbol: string;
}

const eventConfig: Record<string, { icon: typeof DollarSign; color: string; bgColor: string; label: string }> = {
  coupon_payment: { icon: DollarSign, color: "text-blue-400", bgColor: "bg-blue-400/10", label: "Coupon Payment" },
  maturity: { icon: Clock, color: "text-red-400", bgColor: "bg-red-400/10", label: "Maturity" },
  nav_update: { icon: TrendingUp, color: "text-emerald-400", bgColor: "bg-emerald-400/10", label: "NAV Update" },
  report: { icon: FileText, color: "text-purple-400", bgColor: "bg-purple-400/10", label: "Report" },
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

export default function UpcomingEvents() {
  const [events, setEvents] = useState<UpcomingEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [, setTick] = useState(0);

  useEffect(() => {
    getUpcomingEvents(5)
      .then(setEvents)
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  // Tick every 60s to update countdowns
  useEffect(() => {
    const interval = setInterval(() => setTick((t) => t + 1), 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/20 p-8 flex items-center justify-center">
        <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/20 p-8 text-center">
        <p className="text-sm text-muted-foreground">No upcoming events scheduled</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/40 bg-card/20 divide-y divide-border/20">
      {events.map((event) => {
        const config = eventConfig[event.event_type] || eventConfig.report;
        const Icon = config.icon;
        const countdown = formatCountdown(event.scheduled_at);

        return (
          <Link
            key={event.id}
            href={`/assets/${event.asset_id}`}
            className="flex items-center gap-4 px-5 py-3.5 hover:bg-card/40 transition-colors first:rounded-t-xl last:rounded-b-xl"
          >
            <div className={`w-8 h-8 rounded-lg ${config.bgColor} flex items-center justify-center flex-shrink-0`}>
              <Icon className={`w-4 h-4 ${config.color}`} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{config.label}</span>
                <span className="text-xs text-muted-foreground/60">·</span>
                <span className="text-xs text-muted-foreground truncate">{event.asset_name}</span>
              </div>
              <p className="text-[11px] text-muted-foreground font-mono mt-0.5">
                {new Date(event.scheduled_at).toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                  year: "numeric",
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
            </div>
            <span
              className={`text-xs font-mono font-medium px-2.5 py-1 rounded-full flex-shrink-0 ${
                countdown.overdue
                  ? "text-red-400 bg-red-400/10"
                  : "text-amber-400 bg-amber-400/10"
              }`}
            >
              {countdown.text}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
