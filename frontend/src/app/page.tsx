"use client";

import { useState, useEffect } from "react";
import AssetCard from "@/components/AssetCard";
import { getAssets, checkHealth } from "@/lib/api";
import Link from "next/link";

interface Asset {
  id: number;
  name: string;
  symbol: string;
  token_id: string | null;
  asset_type: string;
  total_supply: number;
  decimals: number;
  coupon_rate: number;
  maturity_date: string | null;
  nav: number;
  status: string;
  jurisdiction: string;
  investor_type: string;
  created_at: string;
}

export default function Dashboard() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        await checkHealth();
        setConnected(true);
        const data = await getAssets();
        setAssets(data);
      } catch {
        setConnected(false);
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const activeAssets = assets.filter((a) => a.status === "active");
  const totalAUM = assets.reduce((sum, a) => sum + a.nav, 0);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Autonomous RWA lifecycle management</p>
        </div>
        <div className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border ${
          connected
            ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/5"
            : "text-red-400 border-red-500/20 bg-red-500/5"
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${connected ? "bg-emerald-400" : "bg-red-400"}`} />
          {connected ? "Connected" : "Offline"}
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        <StatCard label="Total AUM" value={`$${totalAUM.toLocaleString()}`} highlight />
        <StatCard label="Active" value={String(activeAssets.length)} />
        <StatCard label="Total Assets" value={String(assets.length)} />
        <StatCard label="Network" value="Testnet" />
      </div>

      {/* Assets */}
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : assets.length === 0 ? (
        <div className="rounded-xl border border-border/40 bg-card/20 p-16 text-center">
          <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
            <svg className="w-7 h-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </div>
          <p className="text-base font-medium mb-1.5">No assets yet</p>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
            Use the Agent to tokenize your first real-world asset on Hedera
          </p>
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 text-sm text-primary-foreground bg-primary hover:bg-primary/90 px-5 py-2.5 rounded-xl transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
            </svg>
            Open Agent
          </Link>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Assets</p>
            <Link
              href="/chat"
              className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.5v15m7.5-7.5h-15" />
              </svg>
              New Asset
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border px-5 py-4 ${
      highlight
        ? "border-primary/20 bg-primary/5"
        : "border-border/40 bg-card/20"
    }`}>
      <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className={`text-xl font-semibold mt-1 tracking-tight ${highlight ? "text-gradient" : ""}`}>{value}</p>
    </div>
  );
}
