"use client";

import AppSidebar from "@/components/layout/app-sidebar";
import AppHeader from "@/components/layout/app-header";
import { WalletProvider, useWallet } from "@/contexts/wallet-context";

function ConnectGate({ children }: { children: React.ReactNode }) {
  const { isConnected, isConnecting, connect, connectDemo } = useWallet();

  if (!isConnected) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-dots">
        <div className="max-w-md w-full mx-auto text-center px-6">
          {/* Logo */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <svg width="36" height="36" viewBox="0 0 28 28" fill="none">
              <rect width="28" height="28" rx="8" fill="#8259ef" />
              <path d="M8 9.5h4.5v9H8v-2.25h2.25v-4.5H8V9.5zM15.5 9.5H20v2.25h-2.25v4.5H20v2.25h-4.5v-9z" fill="white" />
            </svg>
            <span className="text-xl font-semibold tracking-tight">Lamina</span>
          </div>

          <div className="rounded-xl border border-border/50 bg-card/30 p-8">
            <div className="w-14 h-14 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mx-auto mb-5">
              <svg className="w-7 h-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M21 12a2.25 2.25 0 00-2.25-2.25H15a3 3 0 11-6 0H5.25A2.25 2.25 0 003 12m18 0v6a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 18v-6m18 0V9M3 12V9m18 0a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 9m18 0V6a2.25 2.25 0 00-2.25-2.25H5.25A2.25 2.25 0 003 6v3" />
              </svg>
            </div>

            <h2 className="text-lg font-semibold mb-2">Connect Your Wallet</h2>
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              Connect your Hedera wallet to access the RWA management dashboard. All operations are executed on Hedera Testnet.
            </p>

            {/* HashPack button */}
            <button
              onClick={connect}
              disabled={isConnecting}
              className="w-full inline-flex items-center justify-center gap-2.5 text-sm font-medium text-primary-foreground bg-primary hover:bg-primary/90 px-5 py-3 rounded-xl transition-colors disabled:opacity-60 glow-purple"
            >
              {isConnecting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 12a2.25 2.25 0 00-2.25-2.25H15a3 3 0 11-6 0H5.25A2.25 2.25 0 003 12" />
                    <rect x="3" y="12" width="18" height="6" rx="2" />
                  </svg>
                  Connect with HashPack
                </>
              )}
            </button>

            {/* Divider */}
            <div className="flex items-center gap-3 my-4">
              <div className="flex-1 h-px bg-border/50" />
              <span className="text-[10px] text-muted-foreground/50 uppercase tracking-wider">or</span>
              <div className="flex-1 h-px bg-border/50" />
            </div>

            {/* Demo mode button */}
            <button
              onClick={connectDemo}
              disabled={isConnecting}
              className="w-full inline-flex items-center justify-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground border border-border/50 hover:border-border px-5 py-3 rounded-xl transition-all disabled:opacity-60"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Demo Mode
            </button>

            <p className="text-[10px] text-muted-foreground/60 mt-4">
              Demo mode uses testnet operator account for preview
            </p>
          </div>

          <div className="flex items-center justify-center gap-2 mt-6 text-[11px] text-muted-foreground">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            Hedera Testnet
          </div>
        </div>
      </div>
    );
  }

  return (
    <>
      <AppSidebar />
      <div className="ml-[220px] min-h-screen flex flex-col bg-dots">
        <AppHeader />
        <main className="flex-1">{children}</main>
      </div>
    </>
  );
}

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <WalletProvider>
      <ConnectGate>{children}</ConnectGate>
    </WalletProvider>
  );
}
