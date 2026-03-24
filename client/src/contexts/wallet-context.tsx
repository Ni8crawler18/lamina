"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";

interface WalletState {
  address: string | null;
  isConnected: boolean;
  isConnecting: boolean;
  connectionMode: "hashpack" | "demo" | null;
  connect: () => void;
  connectDemo: () => void;
  disconnect: () => void;
}

const WalletContext = createContext<WalletState>({
  address: null,
  isConnected: false,
  isConnecting: false,
  connectionMode: null,
  connect: () => {},
  connectDemo: () => {},
  disconnect: () => {},
});

const WALLETCONNECT_PROJECT_ID =
  process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "";

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionMode, setConnectionMode] = useState<"hashpack" | "demo" | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hashconnectRef = useRef<any>(null);
  const initedRef = useRef(false);

  // Initialize HashConnect lazily (only on first real connect)
  const getHashConnect = useCallback(async () => {
    if (hashconnectRef.current) return hashconnectRef.current;
    if (typeof window === "undefined") return null;

    try {
      const { HashConnect } = await import("hashconnect");
      const { LedgerId } = await import("@hashgraph/sdk");

      const hc = new HashConnect(
        LedgerId.TESTNET,
        WALLETCONNECT_PROJECT_ID,
        {
          name: "Lamina",
          description: "Autonomous RWA Lifecycle Agent on Hedera",
          icons: [],
          url: typeof window !== "undefined" ? window.location.origin : "",
        },
        false
      );

      // Register events before init
      hc.pairingEvent.on((data: { accountIds: string[] }) => {
        if (data.accountIds && data.accountIds.length > 0) {
          setAddress(data.accountIds[0]);
          setConnectionMode("hashpack");
          setIsConnecting(false);
          // Close the modal after successful pairing
          try { hc.closePairingModal?.(); } catch { /* ignore */ }
        }
      });

      hc.disconnectionEvent.on(() => {
        setAddress(null);
        setConnectionMode(null);
      });

      // Init with timeout
      await Promise.race([
        hc.init(),
        new Promise((_, reject) => setTimeout(() => reject(new Error("HashConnect init timeout")), 10000))
      ]);
      hashconnectRef.current = hc;
      return hc;
    } catch (err) {
      console.error("HashConnect init failed:", err);
      return null;
    }
  }, []);

  // Restore session on mount
  useEffect(() => {
    if (initedRef.current) return;
    initedRef.current = true;

    // Check for saved demo session
    if (typeof window !== "undefined") {
      const saved = sessionStorage.getItem("lamina_wallet");
      if (saved) {
        try {
          const data = JSON.parse(saved);
          setAddress(data.address);
          setConnectionMode(data.mode);
        } catch { /* ignore */ }
      }
    }
  }, []);

  // Persist to sessionStorage
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (address && connectionMode) {
      sessionStorage.setItem(
        "lamina_wallet",
        JSON.stringify({ address, mode: connectionMode })
      );
    } else {
      sessionStorage.removeItem("lamina_wallet");
    }
  }, [address, connectionMode]);

  // Connect via HashPack
  const connect = useCallback(async () => {
    setIsConnecting(true);
    try {
      const hc = await getHashConnect();
      if (hc) {
        // Try direct extension connection first, fall back to pairing modal
        try {
          await hc.connectToLocalWallet();
        } catch {
          // Extension not available — show WalletConnect pairing modal
          hc.openPairingModal();
        }
        // Auto-cancel connecting state after 30s if no pairing happens
        setTimeout(() => {
          setIsConnecting((prev) => {
            if (prev) console.warn("Pairing timeout — use Demo Mode");
            return false;
          });
        }, 30000);
      } else {
        console.warn("HashConnect unavailable, falling back to demo mode");
        setAddress("0.0.8003096");
        setConnectionMode("demo");
        setIsConnecting(false);
      }
    } catch (err) {
      console.error("Connect failed:", err);
      setIsConnecting(false);
    }
  }, [getHashConnect]);

  // Connect in demo mode
  const connectDemo = useCallback(() => {
    setIsConnecting(true);
    setTimeout(() => {
      setAddress("0.0.8003096");
      setConnectionMode("demo");
      setIsConnecting(false);
    }, 400);
  }, []);

  // Disconnect
  const disconnect = useCallback(async () => {
    if (connectionMode === "hashpack" && hashconnectRef.current) {
      try {
        await hashconnectRef.current.disconnect();
      } catch { /* ignore */ }
    }
    setAddress(null);
    setConnectionMode(null);
    hashconnectRef.current = null;
  }, [connectionMode]);

  return (
    <WalletContext.Provider
      value={{
        address,
        isConnected: !!address,
        isConnecting,
        connectionMode,
        connect,
        connectDemo,
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
