"use client";

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import { CHAINS, LIVE_CHAINS, chainBySlug, type ChainBrand } from "@/lib/chains";

interface ChainState {
  active: ChainBrand;
  chains: ChainBrand[]; // live chains, for the toggle
  setChain: (slug: string) => void;
  switchWalletNetwork: () => Promise<void>; // ask the wallet to switch to `active`
}

const DEFAULT = LIVE_CHAINS[0] ?? CHAINS[0];

const ChainContext = createContext<ChainState>({
  active: DEFAULT,
  chains: LIVE_CHAINS,
  setChain: () => {},
  switchWalletNetwork: async () => {},
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function eth(): any {
  return typeof window === "undefined" ? undefined : (window as any).ethereum;
}

/** Ask the wallet to switch to the EVM chain, adding it first if unknown (4902).
 *  Backend signs txs, so this is a convenience — failures are swallowed. */
async function trySwitchEvmNetwork(chain: ChainBrand) {
  const provider = eth();
  if (!provider || chain.family !== "evm" || !chain.chainId) return;
  const hexId = "0x" + chain.chainId.toString(16);
  try {
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hexId }] });
  } catch (err: unknown) {
    // 4902 = chain not added to the wallet → add it, then it becomes active.
    const code = (err as { code?: number })?.code;
    if (code === 4902 && chain.rpc) {
      try {
        await provider.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: hexId,
            chainName: `${chain.name} (Laminaa testnet)`,
            nativeCurrency: { name: chain.nativeSymbol || "ETH", symbol: chain.nativeSymbol || "ETH", decimals: 18 },
            rpcUrls: [chain.rpc],
            blockExplorerUrls: chain.explorer ? [chain.explorer] : undefined,
          }],
        });
      } catch {
        /* user declined add — ignore, backend still settles */
      }
    }
    /* other errors (user declined switch) — ignore */
  }
}

export function ChainProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<ChainBrand>(DEFAULT);
  const inited = useRef(false);

  useEffect(() => {
    if (inited.current) return;
    inited.current = true;
    const saved = typeof window !== "undefined" ? localStorage.getItem("Laminaa_chain") : null;
    const found = chainBySlug(saved);
    if (found && found.live) setActive(found);
  }, []);

  const setChain = useCallback((slug: string) => {
    const next = chainBySlug(slug);
    if (!next) return;
    setActive(next);
    if (typeof window !== "undefined") localStorage.setItem("Laminaa_chain", slug);
    void trySwitchEvmNetwork(next);
  }, []);

  const switchWalletNetwork = useCallback(async () => {
    await trySwitchEvmNetwork(active);
  }, [active]);

  return (
    <ChainContext.Provider value={{ active, chains: LIVE_CHAINS, setChain, switchWalletNetwork }}>
      {children}
    </ChainContext.Provider>
  );
}

export function useChain() {
  return useContext(ChainContext);
}
