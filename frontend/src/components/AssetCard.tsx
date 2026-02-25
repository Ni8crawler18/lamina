"use client";

import Link from "next/link";

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
    active: "bg-emerald-500/10 text-emerald-400",
    matured: "bg-blue-500/10 text-blue-400",
    cancelled: "bg-red-500/10 text-red-400",
  }[asset.status] || "bg-muted text-muted-foreground";

  const faceValue = asset.total_supply / Math.pow(10, asset.decimals);

  return (
    <Link href={`/asset/${asset.id}`}>
      <div className="group rounded-xl border border-border/50 bg-card/30 p-5 hover:border-primary/30 hover:bg-card/50 transition-all duration-200 cursor-pointer">
        {/* Top row: name + status */}
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-sm font-medium">{asset.name}</p>
            <p className="font-mono text-xs text-muted-foreground mt-0.5">{asset.symbol}</p>
          </div>
          <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusColor}`}>
            {asset.status}
          </span>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
          <Metric label="Face Value" value={`$${faceValue.toLocaleString()}`} />
          <Metric label="NAV" value={`$${asset.nav.toLocaleString()}`} />
          <Metric label="Coupon" value={`${(asset.coupon_rate * 100).toFixed(2)}%`} />
          <Metric label="Jurisdiction" value={asset.jurisdiction} />
        </div>

        {/* Footer: token ID */}
        {asset.token_id && (
          <p className="font-mono text-[10px] text-muted-foreground/60 mt-4 pt-3 border-t border-border/30">
            {asset.token_id}
          </p>
        )}
      </div>
    </Link>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="font-medium text-sm mt-0.5">{value}</p>
    </div>
  );
}
