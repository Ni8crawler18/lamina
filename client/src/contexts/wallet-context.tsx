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

export type AuthMode = "metamask" | "hashpack" | "phantom" | "google" | "demo";
export type Family = "evm" | "hedera" | "solana";

interface WalletState {
  address: string | null; // EVM 0x… or Hedera 0.0.x (null for Google identity)
  email: string | null; // Google
  name: string | null; // Google display name
  family: Family | null;
  chainId: number | null; // EVM numeric chain id reported by the wallet
  mode: AuthMode | null;
  ownerId: string | null; // issuer identity for asset attribution (address or email)
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  connectMetaMask: () => Promise<void>;
  connectHashPack: () => Promise<void>;
  connectPhantom: () => Promise<void>;
  connectGoogle: () => Promise<void>;
  connectDemo: () => void;
  disconnect: () => void;
}

const noop = () => {};
const WalletContext = createContext<WalletState>({
  address: null,
  email: null,
  name: null,
  family: null,
  chainId: null,
  mode: null,
  ownerId: null,
  isConnected: false,
  isConnecting: false,
  error: null,
  connectMetaMask: async () => {},
  connectHashPack: async () => {},
  connectPhantom: async () => {},
  connectGoogle: async () => {},
  connectDemo: noop,
  disconnect: noop,
});

const WALLETCONNECT_PROJECT_ID = process.env.NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID || "";
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const DEMO_ADDRESS = "0xFa3e5d58ea338A274B7d739117AFfAe80168A429"; // testnet operator (preview only)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function win(): any {
  return typeof window === "undefined" ? undefined : (window as any);
}

// ── EVM provider discovery (EIP-6963) ─────────────────────────
// Brave, Coinbase Wallet and MetaMask all inject into window.ethereum and
// clobber each other. EIP-6963 lets each wallet announce itself so we can
// pick MetaMask deterministically, with a legacy `.providers` fallback.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const discovered: { rdns: string; name: string; provider: any }[] = [];
if (typeof window !== "undefined") {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  window.addEventListener("eip6963:announceProvider", (e: any) => {
    const d = e?.detail;
    if (d?.info?.rdns && !discovered.some((x) => x.rdns === d.info.rdns)) {
      discovered.push({ rdns: d.info.rdns, name: d.info.name, provider: d.provider });
    }
  });
  window.dispatchEvent(new Event("eip6963:requestProvider"));
}

/** Resolve the best EVM provider: MetaMask first, else any injected wallet. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function resolveEvmProvider(): Promise<{ provider: any; label: string } | null> {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event("eip6963:requestProvider"));
    await new Promise((r) => setTimeout(r, 120)); // let wallets respond
  }
  const mm = discovered.find((d) => d.rdns === "io.metamask");
  if (mm) return { provider: mm.provider, label: "MetaMask" };
  if (discovered.length) return { provider: discovered[0].provider, label: discovered[0].name };

  // Legacy fallback: window.ethereum (possibly an array of providers)
  const eth = win()?.ethereum;
  if (!eth) return null;
  if (Array.isArray(eth.providers)) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const inj = eth.providers.find((p: any) => p.isMetaMask) || eth.providers[0];
    return { provider: inj, label: inj?.isMetaMask ? "MetaMask" : "Wallet" };
  }
  return { provider: eth, label: eth.isMetaMask ? "MetaMask" : eth.isBraveWallet ? "Brave Wallet" : "Wallet" };
}

let gsiPromise: Promise<void> | null = null;
function loadGsi(): Promise<void> {
  if (gsiPromise) return gsiPromise;
  gsiPromise = new Promise<void>((resolve, reject) => {
    if (win()?.google?.accounts?.id) return resolve();
    const s = document.createElement("script");
    s.src = "https://accounts.google.com/gsi/client";
    s.async = true;
    s.defer = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Failed to load Google sign-in"));
    document.head.appendChild(s);
  });
  return gsiPromise;
}

// decode a Google JWT credential payload without a dependency
function decodeJwt(token: string): Record<string, string> {
  const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(decodeURIComponent(escape(atob(part))));
}

export function WalletProvider({ children }: { children: ReactNode }) {
  const [address, setAddress] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [name, setName] = useState<string | null>(null);
  const [family, setFamily] = useState<Family | null>(null);
  const [chainId, setChainId] = useState<number | null>(null);
  const [mode, setMode] = useState<AuthMode | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const hashconnectRef = useRef<any>(null);
  const initedRef = useRef(false);

  const reset = useCallback(() => {
    setAddress(null);
    setEmail(null);
    setName(null);
    setFamily(null);
    setChainId(null);
    setMode(null);
  }, []);

  // ── Restore session ──────────────────────────────────────────
  useEffect(() => {
    if (initedRef.current) return;
    initedRef.current = true;
    const saved = win()?.sessionStorage?.getItem("lamina_auth");
    if (saved) {
      try {
        const d = JSON.parse(saved);
        setMode(d.mode ?? null);
        setAddress(d.address ?? null);
        setEmail(d.email ?? null);
        setName(d.name ?? null);
        setFamily(d.family ?? null);
        setChainId(d.chainId ?? null);
      } catch { /* ignore */ }
    }
  }, []);

  // ── Persist session ──────────────────────────────────────────
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (mode) {
      sessionStorage.setItem(
        "lamina_auth",
        JSON.stringify({ mode, address, email, name, family, chainId })
      );
    } else {
      sessionStorage.removeItem("lamina_auth");
    }
  }, [mode, address, email, name, family, chainId]);

  // ── MetaMask (EVM) ───────────────────────────────────────────
  const connectMetaMask = useCallback(async () => {
    setError(null);
    setIsConnecting(true);
    try {
      const resolved = await resolveEvmProvider();
      if (!resolved?.provider) {
        setError("No EVM wallet detected. Install MetaMask (or enable Brave Wallet) and retry.");
        setIsConnecting(false);
        return;
      }
      const eth = resolved.provider;
      const accounts: string[] = await eth.request({ method: "eth_requestAccounts" });
      const hex = await eth.request({ method: "eth_chainId" });
      if (!accounts?.length) throw new Error("No account returned");
      setAddress(accounts[0]);
      setChainId(parseInt(hex, 16));
      setFamily("evm");
      setMode("metamask");

      // live updates
      eth.removeAllListeners?.("accountsChanged");
      eth.removeAllListeners?.("chainChanged");
      eth.on?.("accountsChanged", (accs: string[]) => {
        if (!accs?.length) reset();
        else setAddress(accs[0]);
      });
      eth.on?.("chainChanged", (cid: string) => setChainId(parseInt(cid, 16)));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Wallet connection failed";
      // EIP-1193 user-rejected (4001) → friendlier copy
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.code === 4001 ? "Connection request rejected in your wallet." : msg);
    } finally {
      setIsConnecting(false);
    }
  }, [reset]);

  // ── HashPack (Hedera) ────────────────────────────────────────
  const getHashConnect = useCallback(async () => {
    if (hashconnectRef.current) return hashconnectRef.current;
    if (typeof window === "undefined") return null;
    try {
      const { HashConnect } = await import("hashconnect");
      const { LedgerId } = await import("@hashgraph/sdk");
      const hc = new HashConnect(
        LedgerId.TESTNET,
        WALLETCONNECT_PROJECT_ID,
        { name: "Lamina", description: "Autonomous RWA Lifecycle Agent", icons: [], url: window.location.origin },
        false
      );
      hc.pairingEvent.on((data: { accountIds: string[] }) => {
        if (data.accountIds?.length) {
          setAddress(data.accountIds[0]);
          setFamily("hedera");
          setMode("hashpack");
          setIsConnecting(false);
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          try { (hc as any).closePairingModal?.(); } catch { /* ignore */ }
        }
      });
      hc.disconnectionEvent.on(() => reset());
      await Promise.race([
        hc.init(),
        new Promise((_, rej) => setTimeout(() => rej(new Error("HashConnect init timeout")), 10000)),
      ]);
      hashconnectRef.current = hc;
      return hc;
    } catch (err) {
      console.error("HashConnect init failed:", err);
      return null;
    }
  }, [reset]);

  const connectHashPack = useCallback(async () => {
    setError(null);
    setIsConnecting(true);
    try {
      const hc = await getHashConnect();
      if (!hc) {
        setError("HashPack unavailable. Install the HashPack extension or use Demo mode.");
        setIsConnecting(false);
        return;
      }
      try {
        await hc.connectToLocalWallet();
      } catch {
        hc.openPairingModal();
      }
      setTimeout(() => setIsConnecting((p) => (p ? false : p)), 30000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "HashPack connection failed");
      setIsConnecting(false);
    }
  }, [getHashConnect]);

  // ── Phantom (Solana) ─────────────────────────────────────────
  const connectPhantom = useCallback(async () => {
    setError(null);
    const provider = win()?.phantom?.solana ?? win()?.solana;
    if (!provider?.isPhantom) {
      setError("Phantom not detected. Install the Phantom extension and retry.");
      return;
    }
    setIsConnecting(true);
    try {
      const resp = await provider.connect();
      const pubkey = (resp?.publicKey ?? provider.publicKey)?.toString();
      if (!pubkey) throw new Error("No Solana account returned");
      setAddress(pubkey);
      setFamily("solana");
      setMode("phantom");
      // live updates
      provider.removeAllListeners?.("accountChanged");
      provider.on?.("accountChanged", (pk: { toString(): string } | null) => {
        if (!pk) reset();
        else setAddress(pk.toString());
      });
      provider.on?.("disconnect", () => reset());
    } catch (e) {
      // Phantom user-rejection → code 4001
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const code = (e as any)?.code;
      setError(code === 4001 ? "Connection request rejected in Phantom." : (e instanceof Error ? e.message : "Phantom connection failed"));
    } finally {
      setIsConnecting(false);
    }
  }, [reset]);

  // ── Google (identity) ────────────────────────────────────────
  const connectGoogle = useCallback(async () => {
    setError(null);
    if (!GOOGLE_CLIENT_ID) {
      setError("Google sign-in not configured — set NEXT_PUBLIC_GOOGLE_CLIENT_ID.");
      return;
    }
    setIsConnecting(true);
    try {
      await loadGsi();
      const google = win().google;
      google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (resp: { credential: string }) => {
          try {
            const p = decodeJwt(resp.credential);
            setEmail(p.email ?? null);
            setName(p.name ?? p.given_name ?? null);
            setAddress(null);
            setFamily(null);
            setMode("google");
          } catch {
            setError("Could not read Google profile.");
          } finally {
            setIsConnecting(false);
          }
        },
      });
      google.accounts.id.prompt((n: { isNotDisplayed?: () => boolean; isSkippedMoment?: () => boolean }) => {
        if (n.isNotDisplayed?.() || n.isSkippedMoment?.()) {
          setIsConnecting(false);
          setError("Google prompt was dismissed. Allow third-party sign-in and retry.");
        }
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Google sign-in failed");
      setIsConnecting(false);
    }
  }, []);

  // ── Demo ─────────────────────────────────────────────────────
  const connectDemo = useCallback(() => {
    setError(null);
    setIsConnecting(true);
    setTimeout(() => {
      setAddress(DEMO_ADDRESS);
      setFamily("evm");
      setMode("demo");
      setIsConnecting(false);
    }, 350);
  }, []);

  const disconnect = useCallback(async () => {
    if (mode === "hashpack" && hashconnectRef.current) {
      try { await hashconnectRef.current.disconnect(); } catch { /* ignore */ }
    }
    if (mode === "phantom") {
      try { await (win()?.phantom?.solana ?? win()?.solana)?.disconnect?.(); } catch { /* ignore */ }
    }
    if (mode === "google" && win()?.google?.accounts?.id) {
      try { win().google.accounts.id.disableAutoSelect(); } catch { /* ignore */ }
    }
    hashconnectRef.current = null;
    reset();
  }, [mode, reset]);

  return (
    <WalletContext.Provider
      value={{
        address,
        email,
        name,
        family,
        chainId,
        mode,
        ownerId: address || email || null,
        isConnected: !!mode,
        isConnecting,
        error,
        connectMetaMask,
        connectHashPack,
        connectPhantom,
        connectGoogle,
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
