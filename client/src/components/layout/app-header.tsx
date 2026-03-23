"use client";

import { usePathname } from "next/navigation";
import { useWallet } from "@/contexts/wallet-context";
import { ExternalLink, LogOut } from "lucide-react";

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/assets": "Asset Management",
  "/liquidity": "Liquidity",
  "/payouts": "Payouts",
  "/reports": "Reports",
  "/history": "Audit History",
  "/chat": "Agent",
  "/pitch": "Pitch Deck",
};

export default function AppHeader() {
  const pathname = usePathname();
  const { address, isConnected, disconnect } = useWallet();

  const title = PAGE_TITLES[pathname] || (pathname.startsWith("/assets/") ? "Asset Detail" : "Lamina");

  return (
    <header className="h-14 border-b border-border/30 flex items-center justify-between px-8">
      <h1 className="text-sm font-medium tracking-tight">{title}</h1>
      {isConnected && (
        <div className="flex items-center gap-3">
          <a
            href={`https://hashscan.io/testnet/account/${address}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground hover:text-primary transition-colors"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            {address}
            <ExternalLink className="w-3 h-3" />
          </a>
          <button
            onClick={disconnect}
            className="text-muted-foreground/50 hover:text-red-400 transition-colors p-1"
            title="Disconnect"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </header>
  );
}
