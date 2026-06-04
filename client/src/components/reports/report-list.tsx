"use client";

import { FileText, Download } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Report {
  id: number;
  asset_id?: number;
  asset_name?: string;
  report_type: string;
  period: string;
  generated_at: string;
  download_url?: string;
}

export default function ReportList({ reports }: { reports: Report[] }) {
  if (reports.length === 0) {
    return (
      <div className="rounded-xl border border-border/40 bg-card/20 p-12 text-center">
        <FileText className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
        <p className="text-sm text-muted-foreground">No reports generated yet</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-border/50 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="border-b border-border/30">
            <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-left px-4 py-3">Asset</th>
            <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-left px-4 py-3">Type</th>
            <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-left px-4 py-3">Period</th>
            <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-left px-4 py-3">Generated</th>
            <th className="text-[10px] text-muted-foreground uppercase tracking-wider font-medium text-right px-4 py-3">Action</th>
          </tr>
        </thead>
        <tbody>
          {reports.map((report) => (
            <tr key={report.id} className="border-b border-border/20 hover:bg-card/50 transition-colors">
              <td className="px-4 py-3 text-sm">{report.asset_name || `Asset #${report.asset_id}`}</td>
              <td className="px-4 py-3">
                <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary capitalize">
                  {report.report_type.replace(/_/g, " ")}
                </span>
              </td>
              <td className="px-4 py-3 text-sm text-muted-foreground">{report.period}</td>
              <td className="px-4 py-3 text-xs text-muted-foreground">
                {report.generated_at ? new Date(report.generated_at + "Z").toLocaleString() : "—"}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => window.open(`${API_URL}${report.download_url || `/api/reports/${report.id}/download`}`, "_blank")}
                  className="text-xs text-primary hover:text-primary/80 transition-colors inline-flex items-center gap-1"
                >
                  <Download className="w-3 h-3" />
                  Download
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
