"use client";

import { useState, useEffect } from "react";
import { getAssets } from "@/lib/api";
import { useChain } from "@/contexts/chain-context";
import PurchaseForm from "@/components/compliance/purchase-form";
import WhitelistForm from "@/components/compliance/whitelist-form";

interface Asset {
  id: number;
  name: string;
  symbol: string;
  token_id: string | null;
  status: string;
}

export default function LiquidityPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChain();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAssets(active.slug);
        setAssets(data.filter((a: Asset) => a.status === "active"));
      } catch (err) {
        console.error("Failed to load assets:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [active.slug]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (assets.length === 0) {
    return (
      <div className="p-8">
        <h1 className="text-[22px] font-semibold tracking-tight mb-2">Liquidity</h1>
        <div className="rounded-xl border border-border/40 bg-card/20 p-16 text-center mt-8">
          <p className="text-sm text-muted-foreground">No active assets. Create an asset first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight">Liquidity</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Purchase tokens and manage investor access</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Purchase Card */}
        <div className="rounded-xl border border-border/50 bg-card/30 p-6">
          <h2 className="text-sm font-semibold mb-1">Purchase Tokens</h2>
          <p className="text-xs text-muted-foreground mb-5">Buy tokens for a whitelisted investor account</p>
          <PurchaseForm assets={assets} />
        </div>

        {/* Whitelist Card */}
        <div className="rounded-xl border border-border/50 bg-card/30 p-6">
          <h2 className="text-sm font-semibold mb-1">Whitelist Investor</h2>
          <p className="text-xs text-muted-foreground mb-5">Add a new investor to the KYC whitelist</p>
          <WhitelistForm assets={assets} />
        </div>
      </div>
    </div>
  );
}
