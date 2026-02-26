"use client";

import { useState } from "react";
import { generateReport } from "@/lib/api";

interface Asset {
  id: number;
  name: string;
  symbol: string;
}

export default function ReportGenerator({ assets, onGenerated }: { assets: Asset[]; onGenerated: () => void }) {
  const [assetId, setAssetId] = useState<number>(assets[0]?.id || 0);
  const [reportType, setReportType] = useState("compliance");
  const [period, setPeriod] = useState("Q1 2026");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleGenerate = async () => {
    setLoading(true);
    setResult(null);
    try {
      await generateReport(assetId, reportType, period);
      setResult({ type: "success", message: `${reportType} report generated for ${period}` });
      onGenerated();
    } catch (err) {
      setResult({ type: "error", message: err instanceof Error ? err.message : "Generation failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-xl border border-border/50 bg-card/30 p-6">
      <h3 className="text-sm font-semibold mb-4">Generate Report</h3>

      <div className="space-y-4">
        <div>
          <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Asset</label>
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

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Report Type</label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
            >
              <option value="compliance">Compliance</option>
              <option value="investor_statement">Investor Statement</option>
              <option value="audit_summary">Audit Summary</option>
            </select>
          </div>
          <div>
            <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
            >
              <option value="Q1 2026">Q1 2026</option>
              <option value="Q4 2025">Q4 2025</option>
              <option value="Q3 2025">Q3 2025</option>
              <option value="Annual 2025">Annual 2025</option>
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
          onClick={handleGenerate}
          disabled={loading || assets.length === 0}
          className="w-full px-4 py-2.5 text-xs text-primary-foreground bg-primary hover:bg-primary/90 rounded-lg transition-colors disabled:opacity-40 flex items-center justify-center gap-2"
        >
          {loading && <span className="w-3 h-3 border border-white/30 border-t-white rounded-full animate-spin" />}
          Generate Report
        </button>
      </div>
    </div>
  );
}
