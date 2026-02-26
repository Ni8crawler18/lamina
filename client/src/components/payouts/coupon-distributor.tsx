"use client";

import { useState } from "react";
import { distributeCoupon } from "@/lib/api";

interface Asset {
  id: number;
  name: string;
  coupon_rate: number;
  nav: number;
}

export default function CouponDistributor({ asset, holderCount, onComplete }: { asset: Asset; holderCount: number; onComplete?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string; details?: unknown } | null>(null);

  const estimatedPayout = asset.nav * asset.coupon_rate / 12; // Monthly

  const handleDistribute = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await distributeCoupon(asset.id);
      const numPaid = res.payments?.filter((p: Record<string, string>) => p.status === "paid").length || holderCount;
      setResult({
        type: "success",
        message: `Coupon distributed to ${numPaid} holder(s). Total: ${res.total_distributed_tinybars || 0} tinybars.`,
        details: res,
      });
      onComplete?.();
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Distribution failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/30 p-6">
      <h3 className="text-sm font-semibold mb-4">Coupon Distribution</h3>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Coupon Rate</p>
          <p className="text-lg font-semibold mt-0.5">{(asset.coupon_rate * 100).toFixed(2)}%</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Holders</p>
          <p className="text-lg font-semibold mt-0.5">{holderCount}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Est. Payout</p>
          <p className="text-lg font-semibold mt-0.5 text-gradient">${estimatedPayout.toLocaleString(undefined, { maximumFractionDigits: 0 })}</p>
        </div>
      </div>

      {result && (
        <div className={`text-xs rounded-lg px-3 py-2.5 border mb-4 ${
          result.type === "success"
            ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : "text-red-400 bg-red-500/10 border-red-500/20"
        }`}>
          {result.message}
        </div>
      )}

      <button
        onClick={handleDistribute}
        disabled={loading || holderCount === 0}
        className="w-full px-4 py-2.5 text-xs text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
        Distribute Coupon
      </button>
    </div>
  );
}
