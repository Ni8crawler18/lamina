"use client";

import { usePathname } from "next/navigation";
import { useWallet } from "@/contexts/wallet-context";
import { useChain } from "@/contexts/chain-context";
import { explorerAddressUrl } from "@/lib/chains";
import ChainToggle from "./chain-toggle";
import { ExternalLink, LogOut, AlertTriangle } from "lucide-react";

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

function shortAddr(a: string) {
  if (a.startsWith("0x") && a.length > 12) return `${a.slice(0, 6)}…${a.slice(-4)}`;
  return a;
}

export default function AppHeader() {
  const pathname = usePathname();
  const { address, email, mode, chainId, family, isConnected, disconnect } = useWallet();
  const { active, switchWalletNetwork } = useChain();

  const title = PAGE_TITLES[pathname] || (pathname.startsWith("/assets/") ? "Asset Detail" : "Laminaa");
  const explorer = address ? explorerAddressUrl(active, address) : null;

  // Wallet on a different EVM network than the active chain (cosmetic — backend signs).
  const wrongNetwork =
    family === "evm" &&
    active.family === "evm" &&
    chainId != null &&
    active.chainId != null &&
    chainId !== active.chainId;

  return (
    <header className="flex h-14 items-center justify-between border-b border-border/30 px-8">
      <h1 className="text-sm font-medium tracking-tight">{title}</h1>

      {isConnected && (
        <div className="flex items-center gap-3">
          {wrongNetwork && (
            <button
              onClick={() => void switchWalletNetwork()}
              className="flex items-center gap-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2.5 py-1.5 text-xs text-amber-400 transition-colors hover:bg-amber-500/20"
              title={`Wallet is on chain ${chainId}; switch to ${active.name}`}
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              Switch to {active.name}
            </button>
          )}
          <ChainToggle />

          {/* identity chip */}
          <div className="flex items-center gap-2 rounded-lg border border-border/60 bg-card/40 px-2.5 py-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            {address ? (
              explorer ? (
                <a href={explorer} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1.5 text-xs font-mono text-muted-foreground transition-colors hover:text-foreground">
                  {shortAddr(address)}
                  <ExternalLink className="h-3 w-3" />
                </a>
              ) : (
                <span className="text-xs font-mono text-muted-foreground">{shortAddr(address)}</span>
              )
            ) : (
              <span className="text-xs text-muted-foreground">{email ?? "Signed in"}</span>
            )}
            {mode && (
              <span className="rounded bg-background px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-muted-foreground/70">{mode}</span>
            )}
          </div>

          <button onClick={disconnect} className="p-1 text-muted-foreground/50 transition-colors hover:text-red-400" title="Sign out">
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </header>
  );
}
