"use client";

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react";
import { CHAINS, LIVE_CHAINS, chainBySlug, type ChainBrand } from "@/lib/chains";

interface ChainState {
  active: ChainBrand;
  chains: ChainBrand[]; // live chains, for the toggle
  setChain: (slug: string) => void;
}

const DEFAULT = LIVE_CHAINS[0] ?? CHAINS[0];

const ChainContext = createContext<ChainState>({
  active: DEFAULT,
  chains: LIVE_CHAINS,
  setChain: () => {},
});

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function eth(): any {
  return typeof window === "undefined" ? undefined : (window as any).ethereum;
}

/** Best-effort: ask MetaMask to switch to the EVM chain. Backend signs txs, so
 *  this is cosmetic — failures are swallowed (chain may not be added to the wallet). */
async function trySwitchEvmNetwork(chain: ChainBrand) {
  const provider = eth();
  if (!provider || chain.family !== "evm" || !chain.chainId) return;
  const hexId = "0x" + chain.chainId.toString(16);
  try {
    await provider.request({ method: "wallet_switchEthereumChain", params: [{ chainId: hexId }] });
  } catch {
    /* chain not in wallet / user declined — ignore, backend still settles */
  }
}

export function ChainProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<ChainBrand>(DEFAULT);
  const inited = useRef(false);

  useEffect(() => {
    if (inited.current) return;
    inited.current = true;
    const saved = typeof window !== "undefined" ? localStorage.getItem("lamina_chain") : null;
    const found = chainBySlug(saved);
    if (found && found.live) setActive(found);
  }, []);

  const setChain = useCallback((slug: string) => {
    const next = chainBySlug(slug);
    if (!next) return;
    setActive(next);
    if (typeof window !== "undefined") localStorage.setItem("lamina_chain", slug);
    void trySwitchEvmNetwork(next);
  }, []);

  return (
    <ChainContext.Provider value={{ active, chains: LIVE_CHAINS, setChain }}>
      {children}
    </ChainContext.Provider>
  );
}

export function useChain() {
  return useContext(ChainContext);
}
