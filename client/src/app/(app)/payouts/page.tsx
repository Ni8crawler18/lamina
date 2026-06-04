"use client";

import { useState, useEffect } from "react";
import { getAssets, getHolders, getEvents } from "@/lib/api";
import { useChain } from "@/contexts/chain-context";
import { useWallet } from "@/contexts/wallet-context";
import CouponDistributor from "@/components/payouts/coupon-distributor";
import MaturityCard from "@/components/payouts/maturity-card";
import { Badge } from "@/components/ui/badge";

interface Asset {
  id: number;
  name: string;
  symbol: string;
  coupon_rate: number;
  nav: number;
  maturity_date: string | null;
  status: string;
}

interface PayoutEvent {
  id: number;
  event_type: string;
  status: string;
  scheduled_at: string;
  executed_at?: string;
}

export default function PayoutsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAsset, setSelectedAsset] = useState<Asset | null>(null);
  const [holderCount, setHolderCount] = useState(0);
  const [payoutHistory, setPayoutHistory] = useState<PayoutEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChain();
  const { ownerId } = useWallet();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAssets(active.slug, ownerId || undefined);
        setAssets(data);
        setSelectedAsset(data.length > 0 ? data[0] : null);
      } catch (err) {
        console.error("Failed to load assets:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [active.slug, ownerId]);

  const [refreshKey, setRefreshKey] = useState(0);

  const refreshDetails = () => setRefreshKey((k) => k + 1);

  useEffect(() => {
    if (!selectedAsset) return;
    const loadDetails = async () => {
      try {
        const [holders, events] = await Promise.all([
          getHolders(selectedAsset.id),
          getEvents(selectedAsset.id),
        ]);
        setHolderCount(holders.length);
        setPayoutHistory(
          events.filter((e: PayoutEvent) =>
            e.event_type === "coupon_payment" || e.event_type === "maturity"
          )
        );
      } catch {
        setHolderCount(0);
        setPayoutHistory([]);
      }
    };
    loadDetails();
  }, [selectedAsset, refreshKey]);

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
        <h1 className="text-[22px] font-semibold tracking-tight mb-2">Payouts</h1>
        <div className="rounded-xl border border-border/40 bg-card/20 p-16 text-center mt-8">
          <p className="text-sm text-muted-foreground">No assets yet. Create an asset first.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight">Payouts</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Coupon distribution and maturity settlement</p>
      </div>

      {/* Asset selector */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {assets.map((a) => (
          <button
            key={a.id}
            onClick={() => setSelectedAsset(a)}
            className={`px-3 py-1.5 text-xs rounded-lg border transition-all ${
              selectedAsset?.id === a.id
                ? "border-primary/30 bg-primary/10 text-foreground"
                : "border-border/50 text-muted-foreground hover:text-foreground hover:border-border"
            }`}
          >
            {a.name} ({a.symbol})
          </button>
        ))}
      </div>

      {selectedAsset && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <CouponDistributor asset={selectedAsset} holderCount={holderCount} onComplete={() => {
              refreshDetails();
            }} />
            <MaturityCard asset={selectedAsset} onComplete={() => {
              getAssets(active.slug, ownerId || undefined).then(setAssets);
              refreshDetails();
            }} />
          </div>

          {/* Payout History */}
          <div className="rounded-xl border border-border/50 bg-card/30 p-6">
            <h3 className="text-sm font-semibold mb-4">Payout History</h3>
            {payoutHistory.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-8">No payout events yet</p>
            ) : (
              <div className="space-y-1">
                {payoutHistory.map((event) => (
                  <div key={event.id} className="flex items-center justify-between px-4 py-3 rounded-lg hover:bg-card/50 transition-colors">
                    <div>
                      <p className="text-sm">{event.event_type.replace(/_/g, " ")}</p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">
                        {new Date(event.scheduled_at).toLocaleDateString()}
                      </p>
                    </div>
                    <Badge
                      variant="outline"
                      className={
                        event.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : event.status === "cancelled"
                          ? "bg-red-500/10 text-red-400 border-red-500/20"
                          : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      }
                    >
                      {event.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
