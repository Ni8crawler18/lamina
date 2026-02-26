"use client";

import { useState, useEffect, useCallback } from "react";
import { getAssets } from "@/lib/api";
import AssetCard from "@/components/assets/asset-card";
import CreateAssetForm from "@/components/assets/create-asset-form";
import { Plus, Search, X } from "lucide-react";

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

export default function AssetsPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  const loadAssets = useCallback(async () => {
    try {
      const data = await getAssets();
      setAssets(data);
    } catch (err) {
      console.error("Failed to load assets:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const filtered = assets.filter((a) => {
    if (statusFilter !== "all" && a.status !== statusFilter) return false;
    if (search && !a.name.toLowerCase().includes(search.toLowerCase()) && !a.symbol.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Assets</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{assets.length} total assets</p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="inline-flex items-center gap-2 text-xs text-primary-foreground bg-primary hover:bg-primary/90 px-4 py-2 rounded-lg transition-colors"
        >
          <Plus className="w-3.5 h-3.5" />
          Create Asset
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-6">
        <div className="relative flex-1 max-w-xs">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search assets..."
            className="w-full bg-secondary/50 border border-border/50 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-primary/40"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-secondary/50 border border-border/50 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary/40"
        >
          <option value="all">All Status</option>
          <option value="active">Active</option>
          <option value="matured">Matured</option>
        </select>
      </div>

      {/* Asset Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-24">
          <div className="w-5 h-5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-xl border border-border/40 bg-card/20 p-16 text-center">
          <p className="text-sm text-muted-foreground">
            {assets.length === 0 ? "No assets created yet" : "No assets match your filters"}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {filtered.map((asset) => (
            <AssetCard key={asset.id} asset={asset} />
          ))}
        </div>
      )}

      {/* Create Modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowCreate(false)} />
          <div className="relative w-full max-w-lg bg-background border border-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-base font-semibold">Create New Asset</h2>
              <button onClick={() => setShowCreate(false)} className="text-muted-foreground hover:text-foreground">
                <X className="w-4 h-4" />
              </button>
            </div>
            <CreateAssetForm
              onSuccess={() => {
                setShowCreate(false);
                loadAssets();
              }}
              onClose={() => setShowCreate(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
