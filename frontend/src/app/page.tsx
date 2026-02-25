"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import AssetCard from "@/components/AssetCard";
import { getAssets, checkHealth } from "@/lib/api";

interface Asset {
  id: number;
  name: string;
  symbol: string;
  token_id: string | null;
  asset_type: string;
  total_supply: number;
  decimals: number;
  coupon_rate: number;
  maturity_date: string | null;
  nav: number;
  status: string;
  jurisdiction: string;
  investor_type: string;
  created_at: string;
}

export default function Dashboard() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendStatus, setBackendStatus] = useState<"connected" | "disconnected">("disconnected");

  useEffect(() => {
    const load = async () => {
      try {
        await checkHealth();
        setBackendStatus("connected");
        const data = await getAssets();
        setAssets(data);
      } catch {
        setBackendStatus("disconnected");
      } finally {
        setLoading(false);
      }
    };
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  const activeAssets = assets.filter((a) => a.status === "active");
  const totalAUM = assets.reduce((sum, a) => sum + a.nav, 0);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">Autonomous RWA Lifecycle Management</p>
        </div>
        <Badge
          variant="outline"
          className={
            backendStatus === "connected"
              ? "bg-green-500/10 text-green-500 border-green-500/20"
              : "bg-red-500/10 text-red-500 border-red-500/20"
          }
        >
          {backendStatus === "connected" ? "Backend Connected" : "Backend Offline"}
        </Badge>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard title="Total AUM" value={`$${totalAUM.toLocaleString()}`} />
        <StatCard title="Active Assets" value={String(activeAssets.length)} />
        <StatCard title="Total Assets" value={String(assets.length)} />
        <StatCard title="Network" value="Hedera Testnet" />
      </div>

      {/* Asset Grid */}
      {loading ? (
        <div className="text-center py-16 text-muted-foreground">Loading assets...</div>
      ) : assets.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center">
            <h3 className="text-lg font-semibold mb-2">No assets yet</h3>
            <p className="text-muted-foreground mb-4">
              Use the Chat Agent to tokenize your first asset.
            </p>
            <p className="text-sm text-muted-foreground font-mono">
              Try: &quot;Tokenize a $10M 5-year US Treasury bond, US accredited investors only&quot;
            </p>
          </CardContent>
        </Card>
      ) : (
        <div>
          <h2 className="text-lg font-semibold mb-4">Tokenized Assets</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {assets.map((asset) => (
              <AssetCard key={asset.id} asset={asset} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ title, value }: { title: string; value: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm text-muted-foreground font-normal">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold">{value}</p>
      </CardContent>
    </Card>
  );
}
