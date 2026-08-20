"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import HolderTable from "@/components/assets/holder-table";
import ActionLog from "@/components/assets/action-log";
import EventTimeline from "@/components/assets/event-timeline";
import ComplianceStatus from "@/components/compliance/compliance-status";
import Link from "next/link";
import {
  getAsset,
  getHolders,
  getCompliance,
  getAuditLog,
  getEvents,
  distributeCoupon,
  matureAsset,
  generateReport,
  retireCredits,
} from "@/lib/api";
import { chainBySlug, explorerTokenUrl } from "@/lib/chains";

interface Asset {
  id: number;
  chain: string;
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
  metadata_json: string | null;
  created_at: string;
}

function parseMetadata(metadataJson: string | null): Record<string, unknown> {
  if (!metadataJson) return {};
  try {
    return JSON.parse(metadataJson);
  } catch {
    return {};
  }
}

export default function AssetDetail() {
  const params = useParams();
  const assetId = Number(params.id);

  const [asset, setAsset] = useState<Asset | null>(null);
  const [holders, setHolders] = useState<Record<string, unknown>[]>([]);
  const [compliance, setCompliance] = useState(null);
  const [auditLog, setAuditLog] = useState<{ entries: unknown[]; topic_id?: string; chain?: string } | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [retireHolder, setRetireHolder] = useState("");
  const [retireAmount, setRetireAmount] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [assetData, holdersData, complianceData, auditData, eventsData] = await Promise.all([
        getAsset(assetId),
        getHolders(assetId),
        getCompliance(assetId),
        getAuditLog(assetId).catch(() => ({ entries: [] })),
        getEvents(assetId),
      ]);
      setAsset(assetData);
      setHolders(holdersData);
      setCompliance(complianceData);
      setAuditLog(auditData);
      setEvents(eventsData);
    } catch (err) {
      console.error("Failed to load asset data:", err);
    } finally {
      setLoading(false);
    }
  }, [assetId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleAction = async (action: string) => {
    setActionLoading(action);
    try {
      if (action === "coupon") await distributeCoupon(assetId);
      else if (action === "mature") await matureAsset(assetId);
      else if (action === "report") await generateReport(assetId);
      await loadData();
    } catch (err) {
      console.error(`Action ${action} failed:`, err);
    } finally {
      setActionLoading(null);
    }
  };

  const handleRetire = async () => {
    if (!retireHolder || !retireAmount) return;
    setActionLoading("retire");
    try {
      await retireCredits(assetId, retireHolder, Number(retireAmount));
      setRetireAmount("");
      await loadData();
    } catch (err) {
      console.error("Retire failed:", err);
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-3.5rem)]">
        <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
      </div>
    );
  }

  if (!asset) {
    return (
      <div className="p-8">
        <p className="text-sm text-muted-foreground">Asset not found</p>
      </div>
    );
  }

  const faceValue = asset.total_supply / Math.pow(10, asset.decimals);
  const chain = chainBySlug(asset.chain);
  const isHedera = chain?.family === "hedera";
  const tokenUrl = asset.token_id ? explorerTokenUrl(chain, asset.token_id) : null;
  const statusColor = {
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    matured: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    retired: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  }[asset.status] || "bg-muted text-muted-foreground";

  const allLogs = (auditLog?.entries || []) as Record<string, unknown>[];
  const metadata = parseMetadata(asset.metadata_json);
  const isRealEstate = asset.asset_type === "real_estate";
  const isCarbonCredits = asset.asset_type === "carbon_credits";
  const osmUrl =
    isRealEstate && metadata.lat != null && metadata.lng != null
      ? `https://www.openstreetmap.org/?mlat=${metadata.lat}&mlon=${metadata.lng}#map=16/${metadata.lat}/${metadata.lng}`
      : null;

  return (
    <div className="p-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-muted-foreground mb-6">
        <Link href="/dashboard" className="hover:text-foreground transition-colors">Dashboard</Link>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <Link href="/assets" className="hover:text-foreground transition-colors">Assets</Link>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <span className="text-foreground">{asset.name}</span>
      </div>

      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-[22px] font-semibold tracking-tight">{asset.name}</h1>
            <Badge variant="outline" className={statusColor}>
              {asset.status}
            </Badge>
          </div>
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            <span className="font-mono text-xs text-muted-foreground">{asset.symbol}</span>
            <span className="text-muted-foreground/30">|</span>
            {asset.token_id ? (
              tokenUrl ? (
                <a
                  href={tokenUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-primary/70 hover:text-primary inline-flex items-center gap-1 transition-colors"
                >
                  {asset.token_id}
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              ) : (
                <span className="font-mono text-xs text-muted-foreground">{asset.token_id}</span>
              )
            ) : (
              <span className="font-mono text-xs text-muted-foreground">pending</span>
            )}
            {chain && (
              <>
                <span className="text-muted-foreground/30">|</span>
                <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: chain.color }} />
                  {chain.name}
                </span>
              </>
            )}
            {/* Audit trail: Hedera HCS topic links to explorer; EVM audit-topic shown as reference */}
            {auditLog?.topic_id && isHedera && (
              <>
                <span className="text-muted-foreground/30">|</span>
                <a
                  href={`${chain?.explorer || "https://hashscan.io/testnet"}/topic/${auditLog.topic_id}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-xs text-primary/70 hover:text-primary inline-flex items-center gap-1 transition-colors"
                >
                  HCS: {auditLog.topic_id}
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                </a>
              </>
            )}
          </div>
        </div>
        {asset.status === "active" && (
          <div className="flex gap-2">
            {!isCarbonCredits && (
              <ActionButton
                label="Coupon"
                loading={actionLoading === "coupon"}
                disabled={actionLoading !== null}
                onClick={() => handleAction("coupon")}
              />
            )}
            <ActionButton
              label="Report"
              loading={actionLoading === "report"}
              disabled={actionLoading !== null}
              onClick={() => handleAction("report")}
            />
            {!isCarbonCredits && (
              <ActionButton
                label="Mature"
                loading={actionLoading === "mature"}
                disabled={actionLoading !== null}
                onClick={() => handleAction("mature")}
                destructive
              />
            )}
          </div>
        )}
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3 mb-8">
        <MetricCard label="Face Value" value={`$${faceValue.toLocaleString()}`} />
        <MetricCard label="NAV" value={`$${(asset.nav).toLocaleString()}`} />
        {asset.coupon_rate > 0 ? (
          <MetricCard label="Coupon" value={`${((asset.coupon_rate) * 100).toFixed(2)}%`} />
        ) : (
          <MetricCard label="Asset Type" value={asset.asset_type.replace("_", " ")} />
        )}
        <MetricCard label="Jurisdiction" value={asset.jurisdiction} />
      </div>

      {/* Type-specific metadata */}
      {isRealEstate && (metadata.address || osmUrl) && (
        <div className="rounded-xl border border-border/50 bg-card/30 px-5 py-4 mb-8">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-1.5">Property Location</p>
          <p className="text-sm">{(metadata.address as string) || "—"}</p>
          {osmUrl && (
            <a href={osmUrl} target="_blank" rel="noopener noreferrer" className="text-xs text-primary/70 hover:text-primary mt-1 inline-block">
              View on OpenStreetMap ↗
            </a>
          )}
        </div>
      )}

      {isCarbonCredits && (
        <div className="rounded-xl border border-border/50 bg-card/30 px-5 py-4 mb-8">
          <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-2">Credit Details</p>
          <div className="grid grid-cols-3 gap-4 text-sm mb-4">
            <div><span className="text-muted-foreground text-xs block">Registry</span>{(metadata.registry as string) || "—"}</div>
            <div><span className="text-muted-foreground text-xs block">Vintage</span>{(metadata.vintage_year as string) || "—"}</div>
            <div><span className="text-muted-foreground text-xs block">Serial</span>{(metadata.serial_number as string) || "—"}</div>
          </div>
          {asset.status === "active" && (
            <div className="flex items-end gap-2 pt-3 border-t border-border/40">
              <div className="flex-1">
                <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Holder</label>
                <select
                  value={retireHolder}
                  onChange={(e) => setRetireHolder(e.target.value)}
                  className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
                >
                  <option value="">Select holder...</option>
                  {(holders as { account_id: string; balance: number }[])
                    .filter((h) => h.balance > 0)
                    .map((h) => (
                      <option key={h.account_id} value={h.account_id}>
                        {h.account_id} ({h.balance})
                      </option>
                    ))}
                </select>
              </div>
              <div className="w-32">
                <label className="text-[11px] text-muted-foreground uppercase tracking-wider block mb-1.5">Amount</label>
                <input
                  type="number"
                  value={retireAmount}
                  onChange={(e) => setRetireAmount(e.target.value)}
                  className="w-full bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
                />
              </div>
              <ActionButton
                label="Retire"
                loading={actionLoading === "retire"}
                disabled={actionLoading !== null || !retireHolder || !retireAmount}
                onClick={handleRetire}
                destructive
              />
            </div>
          )}
        </div>
      )}

      {/* Maturity Progress */}
      {asset.maturity_date && (
        <MaturityProgressCard
          createdAt={asset.created_at}
          maturityDate={asset.maturity_date as string}
        />
      )}

      {/* Tabs */}
      <Tabs defaultValue="holders">
        <TabsList className="bg-transparent border-b border-border rounded-none p-0 h-auto gap-0">
          <TabTrigger value="holders" count={holders.length}>Holders</TabTrigger>
          <TabTrigger value="activity" count={allLogs.length}>Activity</TabTrigger>
          <TabTrigger value="compliance">Compliance</TabTrigger>
          <TabTrigger value="events" count={events.length}>Events</TabTrigger>
        </TabsList>

        <TabsContent value="holders" className="mt-6">
          <HolderTable holders={holders as never[]} decimals={asset.decimals} chain={chain} />
        </TabsContent>

        <TabsContent value="activity" className="mt-6">
          <ActionLog entries={allLogs as never[]} chain={chain} />
        </TabsContent>

        <TabsContent value="compliance" className="mt-6">
          <ComplianceStatus data={compliance} />
        </TabsContent>

        <TabsContent value="events" className="mt-6">
          <EventTimeline events={events as never[]} chain={chain} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function TabTrigger({ value, children, count }: { value: string; children: React.ReactNode; count?: number }) {
  return (
    <TabsTrigger
      value={value}
      className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none px-4 py-2.5 text-xs"
    >
      {children}
      {count !== undefined && (
        <span className="ml-1.5 text-muted-foreground">{count}</span>
      )}
    </TabsTrigger>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border/50 bg-card/30 px-4 py-3">
      <p className="text-[11px] text-muted-foreground uppercase tracking-wider">{label}</p>
      <p className="text-lg font-semibold mt-0.5 tracking-tight">{value}</p>
    </div>
  );
}

function ActionButton({
  label,
  loading,
  disabled,
  onClick,
  destructive,
}: {
  label: string;
  loading: boolean;
  disabled: boolean;
  onClick: () => void;
  destructive?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-3.5 py-1.5 text-xs rounded-lg border transition-all duration-150 disabled:opacity-40 ${
        destructive
          ? "border-red-500/20 text-red-400 hover:bg-red-500/10"
          : "border-border text-muted-foreground hover:text-foreground hover:bg-card"
      }`}
    >
      {loading ? (
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
          {label}
        </span>
      ) : label}
    </button>
  );
}

function MaturityProgressCard({ createdAt, maturityDate }: { createdAt: string; maturityDate: string }) {
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
    <div className="rounded-xl border border-border/50 bg-card/30 px-5 py-4 mb-8">
      <div className="flex items-center justify-between mb-2">
        <p className="text-[11px] text-muted-foreground uppercase tracking-wider">Maturity Progress</p>
        <span className={`text-xs font-mono ${matured ? "text-red-400" : "text-muted-foreground"}`}>
          {matured ? "Matured" : `${daysRemaining} days remaining`}
        </span>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex-1">
          <div className="w-full h-2 rounded-full bg-border/30">
            <div
              className={`h-full rounded-full transition-all duration-500 ${barColor}`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
        <span className="text-xs font-mono text-muted-foreground w-12 text-right">{progress.toFixed(1)}%</span>
      </div>
      <div className="flex items-center justify-between mt-2">
        <span className="text-[10px] text-muted-foreground/50">
          {new Date(createdAt).toLocaleDateString()}
        </span>
        <span className="text-[10px] text-muted-foreground/50">
          {new Date(maturityDate).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}
