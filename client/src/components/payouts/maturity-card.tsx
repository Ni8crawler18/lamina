"use client";

import { useState } from "react";
import { matureAsset } from "@/lib/api";

interface Asset {
  id: number;
  name: string;
  nav: number;
  maturity_date: string | null;
  status: string;
}

export default function MaturityCard({ asset, onComplete }: { asset: Asset; onComplete?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const maturityDate = asset.maturity_date ? new Date(asset.maturity_date) : null;
  const daysRemaining = maturityDate ? Math.max(0, Math.ceil((maturityDate.getTime() - Date.now()) / 86400000)) : null;

  const handleMature = async () => {
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setLoading(true);
    setResult(null);
    try {
      await matureAsset(asset.id);
      setResult({ type: "success", message: "Maturity settlement complete. Tokens burned, principal returned." });
      onComplete?.();
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Maturity failed" });
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/30 p-6">
      <h3 className="text-sm font-semibold mb-4">Maturity Settlement</h3>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Maturity Date</p>
          <p className="text-lg font-semibold mt-0.5">
            {maturityDate ? maturityDate.toLocaleDateString() : "N/A"}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Days Remaining</p>
          <p className="text-lg font-semibold mt-0.5">{daysRemaining ?? "N/A"}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Face Value</p>
          <p className="text-lg font-semibold mt-0.5">${asset.nav.toLocaleString()}</p>
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

      {asset.status === "active" && (
        <button
          onClick={handleMature}
          disabled={loading}
          className={`w-full px-4 py-2.5 text-xs rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2 ${
            confirming
              ? "text-white bg-red-500 hover:bg-red-600"
              : "text-red-400 border border-red-500/20 hover:bg-red-500/10"
          }`}
        >
          {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
          {confirming ? "Confirm Settlement" : "Execute Maturity"}
        </button>
      )}

      {asset.status === "matured" && (
        <div className="text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-2.5 text-center">
          This asset has been fully settled
        </div>
      )}
    </div>
  );
}
