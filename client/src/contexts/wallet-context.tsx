"use client";

import { createContext, useContext, useState, useCallback, type ReactNode } from "react";

interface WalletState {
  address: string | null;
  isConnected: boolean;
  isConnecting: boolean;
  connect: () => void;
  disconnect: () => void;
}

const WalletContext = createContext<WalletState>({
  address: null,
  isConnected: false,
  isConnecting: false,
  connect: () => {},
  disconnect: () => {},
});

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);

  const connect = useCallback(() => {
    setIsConnecting(true);
    // Demo mode: simulate connection with testnet operator account
    setTimeout(() => {
      setAddress("0.0.8003096");
      setIsConnecting(false);
    }, 500);
  }, []);

  const disconnect = useCallback(() => {
    setAddress(null);
  }, []);

  return (
    <WalletContext.Provider
      value={{
        address,
        isConnected: !!address,
        isConnecting,
        connect,
        disconnect,
      }}
    >
      {children}
    </WalletContext.Provider>
  );
}

export function useWallet() {
  return useContext(WalletContext);
}
