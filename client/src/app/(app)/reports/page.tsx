"use client";

import { useState, useEffect, useCallback } from "react";
import { getAssets, getReports } from "@/lib/api";
import { useChain } from "@/contexts/chain-context";
import { useWallet } from "@/contexts/wallet-context";
import ReportGenerator from "@/components/reports/report-generator";
import ReportList from "@/components/reports/report-list";

interface Asset {
  id: number;
  name: string;
  symbol: string;
}

interface Report {
  id: number;
  asset_id: number;
  asset_name?: string;
  report_type: string;
  period: string;
  generated_at: string;
  download_url?: string;
}

export default function ReportsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [reports, setReports] = useState<Report[]>([]);
  const [loading, setLoading] = useState(true);
  const { active } = useChain();
  const { ownerId } = useWallet();

  const loadReports = useCallback(async (assetList: Asset[]) => {
    try {
      const allReports: Report[] = [];
      for (const asset of assetList) {
        try {
          const assetReports = await getReports(asset.id);
          allReports.push(
            ...assetReports.map((r: Report) => ({ ...r, asset_name: asset.name }))
          );
        } catch {
          // Skip assets with no reports
        }
      }
      setReports(allReports.sort((a, b) => new Date(b.generated_at || 0).getTime() - new Date(a.generated_at || 0).getTime()));
    } catch (err) {
      console.error("Failed to load reports:", err);
    }
  }, []);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await getAssets(active.slug, ownerId || undefined);
        setAssets(data);
        await loadReports(data);
      } catch (err) {
        console.error("Failed to load:", err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [loadReports, active.slug, ownerId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-[22px] font-semibold tracking-tight">Reports</h1>
        <p className="text-sm text-muted-foreground mt-0.5">Generate and download regulatory reports</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-1">
          <ReportGenerator assets={assets} onGenerated={() => loadReports(assets)} />
        </div>
        <div className="lg:col-span-2">
          <h3 className="text-sm font-semibold mb-4">Generated Reports</h3>
          <ReportList reports={reports} />
        </div>
      </div>
    </div>
  );
}
