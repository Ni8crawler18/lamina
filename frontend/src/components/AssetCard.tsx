"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

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
  created_at: string;
}

export default function AssetCard({ asset }: { asset: Asset }) {
  const statusColor = {
    active: "bg-green-500/10 text-green-500 border-green-500/20",
    matured: "bg-blue-500/10 text-blue-500 border-blue-500/20",
    cancelled: "bg-red-500/10 text-red-500 border-red-500/20",
  }[asset.status] || "bg-muted text-muted-foreground";

  const faceValue = asset.total_supply / Math.pow(10, asset.decimals);

  return (
    <Link href={`/asset/${asset.id}`}>
      <Card className="hover:border-primary/50 transition-colors cursor-pointer h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div>
              <CardTitle className="text-base">{asset.name}</CardTitle>
              <p className="text-sm text-muted-foreground font-mono">{asset.symbol}</p>
            </div>
            <Badge variant="outline" className={statusColor}>
              {asset.status}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted-foreground">Face Value</p>
              <p className="font-semibold">${faceValue.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-muted-foreground">NAV</p>
              <p className="font-semibold">${asset.nav.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Coupon</p>
              <p className="font-semibold">{(asset.coupon_rate * 100).toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-muted-foreground">Jurisdiction</p>
              <p className="font-semibold">{asset.jurisdiction}</p>
            </div>
          </div>
          {asset.token_id && (
            <p className="text-xs text-muted-foreground font-mono truncate">
              Token: {asset.token_id}
            </p>
          )}
          {asset.maturity_date && (
            <p className="text-xs text-muted-foreground">
              Matures: {new Date(asset.maturity_date).toLocaleDateString()}
            </p>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
