"use client";

import { useRouter } from "next/navigation";
import { ExternalLink } from "lucide-react";
import { chainBySlug, explorerTokenUrl, explorerName } from "@/lib/chains";

interface Asset {
  id: number;
  chain?: string;
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
  const router = useRouter();
  const chain = chainBySlug(asset.chain);
  const tokenUrl = asset.token_id ? explorerTokenUrl(chain, asset.token_id) : null;
  const statusColor = {
    active: "bg-emerald-500/10 text-emerald-400",
    matured: "bg-blue-500/10 text-blue-400",
    cancelled: "bg-red-500/10 text-red-400",
  }[asset.status] || "bg-muted text-muted-foreground";

  const faceValue = asset.total_supply / Math.pow(10, asset.decimals);

  return (
    <div
      onClick={() => router.push(`/assets/${asset.id}`)}
      className="group rounded-xl border border-border/50 bg-card/30 p-5 hover:border-primary/30 hover:bg-card/50 transition-all duration-200 cursor-pointer"
    >
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

        {/* Maturity progress */}
        {asset.maturity_date && (
          <MaturityProgress createdAt={asset.created_at} maturityDate={asset.maturity_date} />
        )}

        {/* Footer: token ID with explorer link */}
        {asset.token_id && (
          <div className="mt-4 pt-3 border-t border-border/30 flex items-center justify-between gap-2">
            <span className="font-mono text-[10px] text-muted-foreground/60 truncate">
              {asset.token_id}
            </span>
            {tokenUrl && (
              <a
                href={tokenUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="text-[10px] text-primary/50 hover:text-primary transition-colors inline-flex items-center gap-0.5 opacity-0 group-hover:opacity-100 flex-shrink-0"
              >
                <ExternalLink className="w-2.5 h-2.5" />
                {explorerName(chain)}
              </a>
            )}
          </div>
        )}
    </div>
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

function MaturityProgress({ createdAt, maturityDate }: { createdAt: string; maturityDate: string }) {
  const now = Date.now();
  const start = new Date(createdAt).getTime();
  const end = new Date(maturityDate).getTime();
  const total = end - start;
  const elapsed = now - start;
  const progress = total > 0 ? Math.min(Math.max((elapsed / total) * 100, 0), 100) : 0;
  const matured = now >= end;

  const daysRemaining = matured ? 0 : Math.ceil((end - now) / (1000 * 60 * 60 * 24));
  const barColor = matured || progress > 95 ? "bg-red-400" : progress > 80 ? "bg-amber-400" : "bg-primary";

  return (
    <div className="mt-4 pt-3 border-t border-border/30">
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Maturity</span>
        <span className={`text-[10px] font-mono ${matured ? "text-red-400" : "text-muted-foreground"}`}>
          {matured ? "Matured" : `${daysRemaining}d remaining`}
        </span>
      </div>
      <div className="w-full h-1.5 rounded-full bg-border/30">
        <div
          className={`h-full rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
