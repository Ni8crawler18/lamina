"use client";

import { useState, useEffect } from "react";
import Image from "next/image";
import { getAssets } from "@/lib/api";
import { useChain } from "@/contexts/chain-context";
import { CHAINS, type ChainBrand } from "@/lib/chains";

interface Asset {
  id: number;
  chain: string;
  nav: number;
  status: string;
}

interface ChainAgg {
  chain: ChainBrand;
  assets: number;
  active: number;
  aum: number;
}

/** Portfolio rolled up across every network — the cross-chain view of the engine. */
export default function CrossChainSummary() {
  const { active, setChain } = useChain();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const load = () =>
      getAssets()
        .then((d: Asset[]) => alive && setAssets(d))
        .catch(() => alive && setAssets([]))
        .finally(() => alive && setLoading(false));
    load();
    const interval = setInterval(load, 30000);
    return () => { alive = false; clearInterval(interval); };
  }, []);

  const totalAUM = assets.reduce((s, a) => s + (a.nav || 0), 0);
  const activeCount = assets.filter((a) => a.status === "active").length;

  // Per-chain aggregation, only for chains that actually hold assets.
  const byChain: ChainAgg[] = CHAINS.map((chain) => {
    const rows = assets.filter((a) => a.chain === chain.slug);
    return {
      chain,
      assets: rows.length,
      active: rows.filter((a) => a.status === "active").length,
      aum: rows.reduce((s, a) => s + (a.nav || 0), 0),
    };
  })
    .filter((c) => c.assets > 0)
    .sort((a, b) => b.aum - a.aum);

  const networksWithAssets = byChain.length;

  if (loading) {
    return (
      <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 mb-8 flex items-center justify-center h-32">
        <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-primary/20 bg-primary/5 p-6 mb-8">
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="text-xs font-medium text-primary/80 uppercase tracking-wider">Across all networks</p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            One engine · {networksWithAssets} {networksWithAssets === 1 ? "network" : "networks"} with assets
          </p>
        </div>
        <div className="flex items-center gap-6 text-right">
          <div>
            <p className="text-2xl font-semibold tracking-tight text-gradient">${totalAUM.toLocaleString()}</p>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Total AUM</p>
          </div>
          <div>
            <p className="text-2xl font-semibold tracking-tight">{assets.length}</p>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Assets</p>
          </div>
          <div>
            <p className="text-2xl font-semibold tracking-tight">{activeCount}</p>
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Active</p>
          </div>
        </div>
      </div>

      {byChain.length === 0 ? (
        <p className="text-xs text-muted-foreground">No assets issued on any network yet.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {byChain.map(({ chain, assets: n, aum }) => {
            const isActive = chain.slug === active.slug;
            return (
              <button
                key={chain.slug}
                onClick={() => setChain(chain.slug)}
                className={`group flex items-center gap-2.5 rounded-lg border px-3 py-2 transition-all ${
                  isActive
                    ? "border-primary/40 bg-primary/10"
                    : "border-border/50 bg-card/30 hover:border-primary/30 hover:bg-card/50"
                }`}
              >
                <Image src={chain.logo} alt={chain.name} width={18} height={18} className="rounded-sm" />
                <div className="text-left">
                  <p className="text-xs font-medium leading-none">{chain.name}</p>
                  <p className="text-[10px] text-muted-foreground mt-1 leading-none">
                    {n} {n === 1 ? "asset" : "assets"} · ${aum.toLocaleString()}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
