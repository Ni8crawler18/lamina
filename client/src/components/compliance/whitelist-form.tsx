"use client";

import { useState } from "react";
import { addToWhitelist } from "@/lib/api";

interface Asset {
  id: number;
  name: string;
  symbol: string;
}

export default function WhitelistForm({ assets }: { assets: Asset[] }) {
  const [assetId, setAssetId] = useState<number>(assets[0]?.id || 0);
  const [accountId, setAccountId] = useState("");
  const [jurisdiction, setJurisdiction] = useState("US");
  const [investorType, setInvestorType] = useState("accredited");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleSubmit = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await addToWhitelist(assetId, {
        account_id: accountId || undefined,
        jurisdiction,
        investor_type: investorType,
      });
      const acct = res.account_id || res.holder?.account_id || accountId || "auto-created";
      const kyc = res.kyc_status || res.holder?.kyc_status || "approved";
      setResult({
        type: "success",
        message: `Whitelisted: ${acct} — KYC ${kyc}`,
      });
      setAccountId("");
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Whitelist failed" });
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
        <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">
          Account ID <span className="normal-case text-muted-foreground/50">(leave blank to auto-create)</span>
        </label>
        <input
          value={accountId}
          onChange={(e) => setAccountId(e.target.value)}
          placeholder="0.0.12345 or leave blank"
          className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:border-primary/40"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Jurisdiction</label>
          <select
            value={jurisdiction}
            onChange={(e) => setJurisdiction(e.target.value)}
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
            value={investorType}
            onChange={(e) => setInvestorType(e.target.value)}
            className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          >
            <option value="accredited">Accredited</option>
            <option value="institutional">Institutional</option>
            <option value="qualified">Qualified</option>
            <option value="professional">Professional</option>
            <option value="retail">Retail</option>
          </select>
        </div>
      </div>

      {result && (
        <div className={`text-xs rounded-lg px-3 py-2.5 border ${
          result.type === "success"
            ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20"
            : "text-red-400 bg-red-500/10 border-red-500/20"
        }`}>
          {result.message}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full px-4 py-2 text-xs text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
      >
        {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
        Add to Whitelist
      </button>
    </div>
  );
}
