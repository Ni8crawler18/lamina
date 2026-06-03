"use client";

import AppSidebar from "@/components/layout/app-sidebar";
import AppHeader from "@/components/layout/app-header";
import LoginScreen from "@/components/auth/login-screen";
import { WalletProvider, useWallet } from "@/contexts/wallet-context";
import { ChainProvider } from "@/contexts/chain-context";

function Gate({ children }: { children: React.ReactNode }) {
  const { isConnected } = useWallet();

  if (!isConnected) return <LoginScreen />;

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

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <WalletProvider>
      <ChainProvider>
        <Gate>{children}</Gate>
      </ChainProvider>
    </WalletProvider>
  );
}
