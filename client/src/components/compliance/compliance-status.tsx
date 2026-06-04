"use client";

// Matches GET /api/assets/{id}/compliance
interface ComplianceData {
  asset_id: number;
  chain?: string;
  jurisdiction: string;
  total_holders: number;
  whitelisted: number;
  flagged_ofac: number;
  regulations: string[];
  blocked_jurisdictions: string[];
}

const regLabels: Record<string, string> = {
  reg_d: "SEC Reg D",
  reg_s: "SEC Reg S",
  mifid_ii: "MiFID II",
  mifid: "MiFID II",
};

export default function ComplianceStatus({ data }: { data: ComplianceData | null }) {
  if (!data) {
    return (
      <p className="text-sm text-muted-foreground text-center py-12">
        Loading compliance data...
      </p>
    );
  }

  const compliant = (data.flagged_ofac ?? 0) === 0;

  return (
    <div className="space-y-6">
      {/* Status header */}
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium">Compliance Status</p>
        <span className={`text-[10px] font-medium px-2.5 py-0.5 rounded-full ${
          compliant
            ? "bg-emerald-500/10 text-emerald-400"
            : "bg-red-500/10 text-red-400"
        }`}>
          {compliant ? "compliant" : "review needed"}
        </span>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold">{data.whitelisted ?? 0}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Whitelisted</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className="text-2xl font-semibold">{data.total_holders ?? 0}</p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Total Holders</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/30 p-4 text-center">
          <p className={`text-2xl font-semibold ${(data.flagged_ofac ?? 0) > 0 ? "text-red-400" : ""}`}>
            {data.flagged_ofac ?? 0}
          </p>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">OFAC Flags</p>
        </div>
      </div>

      {/* Regulations */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Regulations</p>
        <div className="flex flex-wrap gap-2">
          {(data.regulations || []).length > 0 ? (
            data.regulations.map((reg) => (
              <span key={reg} className="px-2.5 py-1 rounded-lg bg-primary/10 text-primary text-[11px] font-medium">
                {regLabels[reg] || reg.replace(/_/g, " ").toUpperCase()}
              </span>
            ))
          ) : (
            <p className="text-xs text-muted-foreground">No regulations configured</p>
          )}
        </div>
      </div>

      {/* Blocked jurisdictions */}
      <div>
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">Blocked Jurisdictions</p>
        {(data.blocked_jurisdictions || []).length > 0 ? (
          <div className="flex flex-wrap gap-1.5">
            {data.blocked_jurisdictions.map((j) => (
              <span key={j} className="px-2 py-0.5 rounded bg-red-500/10 text-red-400 text-[10px] font-mono">
                {j}
              </span>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">None</p>
        )}
      </div>

      {/* Footer */}
      <div className="flex items-center gap-3 text-xs text-muted-foreground pt-3 border-t border-border/30">
        <span className="px-2 py-0.5 rounded bg-secondary text-[10px] font-medium">{data.jurisdiction}</span>
        <span className="text-muted-foreground/50">|</span>
        <span>Every transfer screened against KYC whitelist + OFAC SDN</span>
      </div>
    </div>
  );
}
