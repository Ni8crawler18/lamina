"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ComplianceData {
  asset_id: number;
  jurisdiction: string;
  investor_type: string;
  total_holders: number;
  whitelisted_holders: number;
  blocked_transfers: number;
  jurisdiction_breakdown: Record<string, number>;
  status: string;
}

export default function ComplianceStatus({ data }: { data: ComplianceData | null }) {
  if (!data) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Loading compliance data...
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Compliance Status</CardTitle>
          <Badge
            variant="outline"
            className={
              data.status === "compliant"
                ? "bg-green-500/10 text-green-500 border-green-500/20"
                : "bg-red-500/10 text-red-500 border-red-500/20"
            }
          >
            {data.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold">{data.whitelisted_holders}</p>
            <p className="text-xs text-muted-foreground">Whitelisted</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold">{data.total_holders}</p>
            <p className="text-xs text-muted-foreground">Total Holders</p>
          </div>
          <div className="text-center p-3 rounded-lg bg-muted/50">
            <p className="text-2xl font-bold text-red-500">{data.blocked_transfers}</p>
            <p className="text-xs text-muted-foreground">Blocked</p>
          </div>
        </div>

        <div>
          <p className="text-sm font-medium mb-2">Jurisdiction Breakdown</p>
          <div className="space-y-1">
            {Object.entries(data.jurisdiction_breakdown).map(([jurisdiction, count]) => (
              <div key={jurisdiction} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{jurisdiction}</span>
                <span className="font-mono">{count}</span>
              </div>
            ))}
            {Object.keys(data.jurisdiction_breakdown).length === 0 && (
              <p className="text-xs text-muted-foreground">No jurisdiction data</p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>Regulation:</span>
          <Badge variant="secondary" className="text-xs">
            {data.jurisdiction === "US" ? "SEC Reg D" : data.jurisdiction === "EU" ? "MiFID II" : data.jurisdiction}
          </Badge>
          <span>|</span>
          <span>Investors: {data.investor_type}</span>
        </div>
      </CardContent>
    </Card>
  );
}
