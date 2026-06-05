"use client";

import { useState, useEffect } from "react";
import AssetCard from "@/components/assets/asset-card";
import UpcomingEvents from "@/components/dashboard/upcoming-events";
import CrossChainSummary from "@/components/dashboard/cross-chain-summary";
import { getAssets, checkHealth } from "@/lib/api";
import Link from "next/link";
import { useWallet } from "@/contexts/wallet-context";
import { useChain } from "@/contexts/chain-context";
import { explorerAddressUrl } from "@/lib/chains";
import { ExternalLink } from "lucide-react";

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
  const { address, email, ownerId } = useWallet();
  const { active } = useChain();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendUp, setBackendUp] = useState(false);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      // Health probe is advisory only — it must never gate the data load
      // (ad-blockers/Brave Shields sometimes block /health as telemetry).
      checkHealth()
        .then(() => alive && setBackendUp(true))
        .catch(() => {});
      try {
        const data = await getAssets(active.slug, ownerId || undefined);
        // A successful asset fetch is itself proof the backend is up.
        if (alive) { setAssets(data); setBackendUp(true); }
      } catch {
        if (alive) setBackendUp(false);
      } finally {
        if (alive) setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => { alive = false; clearInterval(interval); };
  }, [active.slug, ownerId]);

  const explorer = address ? explorerAddressUrl(active, address) : null;

  const activeAssets = assets.filter((a) => a.status === "active");
  const totalAUM = assets.reduce((sum, a) => sum + a.nav, 0);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Overview</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {address ? (
              <>
                Account{" "}
                {explorer ? (
                  <a
                    href={explorer}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-primary/80 hover:text-primary inline-flex items-center gap-1"
                  >
                    {address}
                    <ExternalLink className="w-3 h-3" />
                  </a>
                ) : (
                  <span className="font-mono text-primary/80">{address}</span>
                )}
                {" · "}
                <span className="text-muted-foreground">{active.name}</span>
              </>
            ) : (
              <>Signed in as <span className="text-foreground">{email}</span> · {active.name}</>
            )}
          </p>
        </div>
        {!backendUp && !loading && (
          <div className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full border text-red-400 border-red-500/20 bg-red-500/5">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
            Backend Offline
          </div>
        )}
      </div>

      {/* Cross-chain rollup — portfolio across every network */}
      {backendUp && <CrossChainSummary />}

      {/* Active-chain stats */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          On {active.name}
        </p>
      </div>
      <div className="grid grid-cols-4 gap-3 mb-8">
        <StatCard label="AUM" value={`$${totalAUM.toLocaleString()}`} highlight />
        <StatCard label="Active Assets" value={String(activeAssets.length)} />
        <StatCard label="Total Assets" value={String(assets.length)} />
        <StatCard label="Network" value={active.name} />
      </div>

      {/* Upcoming Events */}
      {!loading && assets.length > 0 && (
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Upcoming Events</p>
            <Link
              href="/history"
              className="text-xs text-primary hover:text-primary/80 transition-colors"
            >
              View All
            </Link>
          </div>
          <UpcomingEvents />
        </div>
      )}

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
          <p className="text-base font-medium mb-1.5">No assets on {active.name} yet</p>
          <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
            Create your first tokenized real-world asset on {active.name}, or use the Agent for natural language commands.
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/assets"
              className="inline-flex items-center gap-2 text-sm text-primary-foreground bg-primary hover:bg-primary/90 px-5 py-2.5 rounded-xl transition-colors"
            >
              Create Asset
            </Link>
            <Link
              href="/chat"
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground border border-border/50 px-5 py-2.5 rounded-xl transition-colors"
            >
              Open Agent
            </Link>
          </div>
        </div>
      ) : (
        <div>
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Assets</p>
            <Link
              href="/assets"
              className="text-xs text-primary hover:text-primary/80 transition-colors flex items-center gap-1"
            >
              View All
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
            {assets.slice(0, 6).map((asset) => (
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
