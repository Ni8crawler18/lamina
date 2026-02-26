"use client";

import { useState } from "react";
import { purchaseTokens, validateTransfer } from "@/lib/api";
import { useWallet } from "@/contexts/wallet-context";

interface Asset {
  id: number;
  name: string;
  symbol: string;
  token_id: string | null;
}

export default function PurchaseForm({ assets }: { assets: Asset[] }) {
  const { address } = useWallet();
  const [assetId, setAssetId] = useState<number>(assets[0]?.id || 0);
  const [accountId, setAccountId] = useState("");
  const [amount, setAmount] = useState("");
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error" | "validation"; message: string } | null>(null);

  const handleValidate = async () => {
    if (!assetId || !accountId || !amount || !address) return;
    setValidating(true);
    setResult(null);
    try {
      const res = await validateTransfer(assetId, address, accountId, Number(amount));
      setResult({
        type: "validation",
        message: res.approved ? "Transfer approved — compliant" : `Transfer denied: ${res.reason}`,
      });
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Validation failed" });
    } finally {
      setValidating(false);
    }
  };

  const handlePurchase = async () => {
    if (!assetId || !accountId || !amount) return;
    setLoading(true);
    setResult(null);
    try {
      const res = await purchaseTokens(assetId, accountId, Number(amount));
      const txId = res.transaction_id || res.transfer?.transaction_id || "confirmed";
      setResult({ type: "success", message: `Purchase complete. TX: ${txId}` });
      setAccountId("");
      setAmount("");
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Purchase failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Select Asset</label>
        <select
          value={assetId}
          onChange={(e) => setAssetId(Number(e.target.value))}
          className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        >
          {assets.map((a) => (
            <option key={a.id} value={a.id}>{a.name} ({a.symbol})</option>
          ))}
        </select>
      </div>

      <div>
        <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Account ID</label>
        <input
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          placeholder="0.0.12345"
          className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary/40"
        />
      </div>

      <div>
        <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Amount (tokens)</label>
        <input
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          placeholder="1000"
          className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        />
      </div>

      {result && (
        <div className={`text-xs rounded-lg px-3 py-2.5 border ${
          result.type === "success"
            ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : result.type === "error"
            ? "text-red-400 bg-red-500/10 border-red-500/20"
            : result.message.includes("approved")
            ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : "text-amber-400 bg-amber-500/10 border-amber-500/20"
        }`}>
          {result.message}
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={handleValidate}
          disabled={validating || !accountId || !amount}
          className="flex-1 px-4 py-2 text-xs border border-border/50 text-muted-foreground hover:text-foreground hover:bg-card rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {validating && <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />}
          Validate
        </button>
        <button
          onClick={handlePurchase}
          disabled={loading || !accountId || !amount}
          className="flex-1 px-4 py-2 text-xs text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
          Purchase
        </button>
      </div>
    </div>
  );
}
