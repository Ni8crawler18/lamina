"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useWallet } from "@/contexts/wallet-context";
import { useChain } from "@/contexts/chain-context";
import {
  LayoutDashboard,
  Coins,
  Droplets,
  Banknote,
  FileText,
  History,
  MessageSquare,
  Presentation,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/assets", label: "Assets", icon: Coins },
  { href: "/liquidity", label: "Liquidity", icon: Droplets },
  { href: "/payouts", label: "Payouts", icon: Banknote },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/history", label: "History", icon: History },
  { href: "/chat", label: "Agent", icon: MessageSquare },
  { href: "/pitch", label: "Pitch", icon: Presentation },
];

function Logo() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 22L4 16.5L14 11L24 16.5L14 22Z" fill="#5a3db5" opacity="0.6"/>
      <path d="M14 18L4 12.5L14 7L24 12.5L14 18Z" fill="#7c5ce7" opacity="0.8"/>
      <path d="M14 14L4 8.5L14 3L24 8.5L14 14Z" fill="#a78bfa"/>
    </svg>
  );
}

export default function AppSidebar() {
  const pathname = usePathname();
  const { address, email, mode } = useWallet();
  const { active } = useChain();

  return (
    <aside className="w-[220px] bg-card/40 border-r border-border/50 flex flex-col h-screen fixed left-0 top-0 z-50">
      <div className="p-5">
        <Link href="/" className="flex items-center gap-2.5">
          <Logo />
          <span className="font-semibold text-[15px] tracking-tight">Laminaa</span>
        </Link>
      </div>

      <nav className="flex-1 px-3 mt-2 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] transition-all duration-150 ${
                active
                  ? "text-foreground bg-primary/10 border border-primary/20"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/50 border border-transparent"
              }`}
            >
              <Icon className={`w-[18px] h-[18px] flex-shrink-0 ${active ? "text-primary" : ""}`} strokeWidth={1.5} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 mx-3 mb-3 rounded-lg bg-secondary/40 border border-border/30">
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          {active.name}
        </div>
        <p className="font-mono text-[11px] text-muted-foreground/60 mt-1 truncate">
          {address || email || "—"}
        </p>
        {mode && (
          <p className="text-[9px] text-amber-400/70 mt-0.5">{mode === "demo" ? "demo mode" : mode}</p>
        )}
      </div>
    </aside>
  );
}
