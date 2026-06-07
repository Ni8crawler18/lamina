"use client";

import { useState } from "react";
import { createAsset } from "@/lib/api";
import { useChain } from "@/contexts/chain-context";
import { useWallet } from "@/contexts/wallet-context";

interface CreateAssetFormProps {
  onSuccess: () => void;
  onClose: () => void;
}

export default function CreateAssetForm({ onSuccess, onClose }: CreateAssetFormProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { active } = useChain();
  const { ownerId } = useWallet();
  // Default maturity: 5 years from today
  const defaultMaturity = new Date(Date.now() + 5 * 365.25 * 86400000).toISOString().split("T")[0];

  const [form, setForm] = useState({
    name: "",
    symbol: "",
    issuer_name: "",
    asset_type: "bond",
    total_supply: "",
    decimals: 2,
    coupon_rate: "",
    maturity_date: "",
    jurisdiction: "US",
    investor_type: "accredited",
  });

  const update = (field: string, value: string | number) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await createAsset({
        ...form,
        chain: active.slug,
        owner: ownerId || undefined,
        issuer_name: form.issuer_name || null,
        total_supply: Number(form.total_supply) * Math.pow(10, form.decimals),
        coupon_rate: Number(form.coupon_rate) / 100,
        maturity_date: form.maturity_date || null,
      });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create asset");
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Name</label>
          <input
            required
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            placeholder="US Treasury Bond 2031"
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Symbol</label>
          <input
            required
            value={form.symbol}
            onChange={(e) => update("symbol", e.target.value.toUpperCase())}
            placeholder="UST31"
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
      </div>

      <div>
        <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Issuer Legal Entity <span className="text-muted-foreground/60 normal-case">(optional, shown on filings)</span></label>
        <input
          value={form.issuer_name}
          onChange={(e) => update("issuer_name", e.target.value)}
          placeholder="Acme Capital Partners LLC"
          className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        />
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Asset Type</label>
          <select
            value={form.asset_type}
            onChange={(e) => update("asset_type", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          >
            <option value="bond">Bond</option>
            <option value="equity">Equity</option>
            <option value="fund">Fund</option>
          </select>
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Total Supply ($)</label>
          <input
            type="number"
            required
            value={form.total_supply}
            onChange={(e) => update("total_supply", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Decimals</label>
          <input
            type="number"
            value={form.decimals}
            onChange={(e) => update("decimals", Number(e.target.value))}
            min={0}
            max={8}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Coupon Rate (%)</label>
          <input
            type="number"
            step="0.01"
            value={form.coupon_rate}
            onChange={(e) => update("coupon_rate", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Maturity Date</label>
          <input
            type="date"
            value={form.maturity_date}
            onChange={(e) => update("maturity_date", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Jurisdiction</label>
          <select
            value={form.jurisdiction}
            onChange={(e) => update("jurisdiction", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          >
            <option value="US">United States</option>
            <option value="EU">European Union</option>
            <option value="UK">United Kingdom</option>
            <option value="SG">Singapore</option>
            <option value="HK">Hong Kong</option>
          </select>
        </div>
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Investor Type</label>
          <select
            value={form.investor_type}
            onChange={(e) => update("investor_type", e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          >
            <option value="accredited">Accredited</option>
            <option value="institutional">Institutional</option>
            <option value="retail">Retail</option>
          </select>
        </div>
      </div>

      {error && (
        <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="flex items-center justify-between gap-3 pt-2">
        <span className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <img src={`${active.logo}?v=7`} alt="" className={`h-3.5 w-3.5 object-contain ${active.family === "hedera" ? "scale-[0.82]" : ""}`} />
          Deploying on <span className="text-foreground">{active.name}</span>
        </span>
        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs text-muted-foreground hover:text-foreground border border-border/50 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-xs text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-40 flex items-center gap-2"
          >
            {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
            {loading ? "Creating..." : "Create Asset"}
          </button>
        </div>
      </div>
    </form>
  );
}
