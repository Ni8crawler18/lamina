"use client";

interface ComplianceData {
  asset_id: number;
  jurisdiction: string;
  investor_type: string;
  total_holders: number;
  whitelisted_holders: number;
  blocked_transfers: number;
  ofac_screenings: number;
  ofac_flags: number;
  jurisdiction_breakdown: Record<string, number>;
  status: string;
}

export default function ComplianceStatus({ data }: { data: ComplianceData | null }) {
  if (!data) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        Loading compliance data...
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Compliance Status</p>
        <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full ${
          data.status === "compliant"
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-red-500/10 text-red-400"
        }`}>
          {data.status}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold">{data.whitelisted_holders}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Whitelisted</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold">{data.total_holders}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Total Holders</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold text-red-400">{data.blocked_transfers}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Blocked</p>
        </div>
      </div>

      {/* OFAC Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold">{data.ofac_screenings ?? 0}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">OFAC Screenings</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold text-red-400">{data.ofac_flags ?? 0}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">OFAC Flags</p>
        </div>
      </div>

      {/* Jurisdiction breakdown */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Jurisdictions</p>
        <div className="space-y-2">
          {Object.entries(data.jurisdiction_breakdown).map(([jurisdiction, count]) => (
            <div key={jurisdiction} className="flex items-center justify-between text-sm px-4 py-2 rounded-lg hover:bg-card/50 transition-colors">
              <span className="text-muted-foreground">{jurisdiction}</span>
              <span className="font-mono text-xs">{count}</span>
            </div>
          ))}
          {Object.keys(data.jurisdiction_breakdown).length === 0 && (
            <p className="text-xs text-muted-foreground">No jurisdiction data</p>
          )}
        </div>
      </div>

      {/* Regulation */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground pt-3 border-t border-border/30">
        <span className="px-2 py-0.5 rounded bg-primary/10 text-primary text-[10px] font-medium">
          {data.jurisdiction === "US" ? "SEC Reg D" : data.jurisdiction === "EU" ? "MiFID II" : data.jurisdiction}
        </span>
        <span className="text-muted-foreground/50">|</span>
        <span>{data.investor_type} investors</span>
      </div>
    </div>
  );
}
