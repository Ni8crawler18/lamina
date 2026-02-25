"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import HolderTable from "@/components/HolderTable";
import ActionLog from "@/components/ActionLog";
import ComplianceStatus from "@/components/ComplianceStatus";
import {
  getAsset,
  getHolders,
  getCompliance,
  getAuditLog,
  getEvents,
  distributeCoupon,
  matureAsset,
  generateReport,
} from "@/lib/api";

export default function AssetDetail() {
  const params = useParams();
  const assetId = Number(params.id);

  const [asset, setAsset] = useState<Record<string, unknown> | null>(null);
  const [holders, setHolders] = useState<Record<string, unknown>[]>([]);
  const [compliance, setCompliance] = useState(null);
  const [auditLog, setAuditLog] = useState<{ hcs_messages: unknown[]; local_log: unknown[] } | null>(null);
  const [events, setEvents] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [assetData, holdersData, complianceData, auditData, eventsData] = await Promise.all([
        getAsset(assetId),
        getHolders(assetId),
        getCompliance(assetId),
        getAuditLog(assetId).catch(() => ({ hcs_messages: [], local_log: [] })),
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

  if (loading) {
    return <div className="p-8 text-muted-foreground">Loading asset...</div>;
  }

  if (!asset) {
    return <div className="p-8 text-red-500">Asset not found</div>;
  }

  const faceValue = (asset.total_supply as number) / Math.pow(10, asset.decimals as number);
  const statusColor = {
    active: "bg-green-500/10 text-green-500 border-green-500/20",
    matured: "bg-blue-500/10 text-blue-500 border-blue-500/20",
  }[asset.status as string] || "bg-muted text-muted-foreground";

  // Merge HCS + local logs for the action feed
  const allLogs = [
    ...(auditLog?.hcs_messages || []),
    ...(auditLog?.local_log || []),
  ] as Record<string, unknown>[];

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{asset.name as string}</h1>
            <Badge variant="outline" className={statusColor}>
              {asset.status as string}
            </Badge>
          </div>
          <p className="text-muted-foreground font-mono text-sm mt-1">
            {asset.symbol as string} &middot; Token: {asset.token_id as string || "pending"}
          </p>
        </div>
        <div className="flex gap-2">
          {asset.status === "active" && (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={actionLoading !== null}
                onClick={() => handleAction("coupon")}
              >
                {actionLoading === "coupon" ? "Distributing..." : "Distribute Coupon"}
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={actionLoading !== null}
                onClick={() => handleAction("report")}
              >
                {actionLoading === "report" ? "Generating..." : "Generate Report"}
              </Button>
              <Button
                variant="destructive"
                size="sm"
                disabled={actionLoading !== null}
                onClick={() => handleAction("mature")}
              >
                {actionLoading === "mature" ? "Processing..." : "Execute Maturity"}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Asset Info Cards */}
      <div className="grid grid-cols-5 gap-4 mb-6">
        <InfoCard label="Face Value" value={`$${faceValue.toLocaleString()}`} />
        <InfoCard label="NAV" value={`$${(asset.nav as number).toLocaleString()}`} />
        <InfoCard label="Coupon Rate" value={`${((asset.coupon_rate as number) * 100).toFixed(1)}%`} />
        <InfoCard label="Jurisdiction" value={asset.jurisdiction as string} />
        <InfoCard
          label="Maturity"
          value={asset.maturity_date ? new Date(asset.maturity_date as string).toLocaleDateString() : "N/A"}
        />
      </div>

      <Separator className="mb-6" />

      {/* Tabs */}
      <Tabs defaultValue="holders">
        <TabsList>
          <TabsTrigger value="holders">Holders ({holders.length})</TabsTrigger>
          <TabsTrigger value="activity">Activity ({allLogs.length})</TabsTrigger>
          <TabsTrigger value="compliance">Compliance</TabsTrigger>
          <TabsTrigger value="events">Events ({events.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="holders" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              <HolderTable holders={holders as never[]} decimals={asset.decimals as number} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Agent Action Log</CardTitle>
              {auditLog && (
                <p className="text-xs text-muted-foreground font-mono">
                  HCS Topic: {(auditLog as Record<string, unknown>).topic_id as string || "N/A"}
                </p>
              )}
            </CardHeader>
            <CardContent>
              <ActionLog entries={allLogs as never[]} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="compliance" className="mt-4">
          <ComplianceStatus data={compliance} />
        </TabsContent>

        <TabsContent value="events" className="mt-4">
          <Card>
            <CardContent className="pt-6">
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">No scheduled events</p>
              ) : (
                <div className="space-y-2">
                  {events.map((event) => (
                    <div key={event.id as number} className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                      <div>
                        <p className="text-sm font-medium">{(event.event_type as string).replace(/_/g, " ")}</p>
                        <p className="text-xs text-muted-foreground">
                          Scheduled: {new Date(event.scheduled_at as string).toLocaleDateString()}
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className={
                          event.status === "completed"
                            ? "bg-green-500/10 text-green-500"
                            : event.status === "cancelled"
                            ? "bg-red-500/10 text-red-500"
                            : "bg-yellow-500/10 text-yellow-500"
                        }
                      >
                        {event.status as string}
                      </Badge>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <Card>
      <CardContent className="pt-4 pb-4">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-lg font-bold mt-1">{value}</p>
      </CardContent>
    </Card>
  );
}
