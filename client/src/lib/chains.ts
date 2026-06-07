// Chains Laminaa deploys to. Logos are recolored to a cohesive blue monochrome
// (see /public/chains/*.png) so the set reads as one enterprise system.
export type ChainBrand = {
  slug: string;
  name: string;
  short: string;
  color: string;
  logo: string;
  family: "evm" | "hedera" | "solana" | "sui";
  chainId?: number; // EVM numeric chain id (for MetaMask network switching)
  explorer?: string; // block explorer base url
  rpc?: string; // public RPC (for wallet_addEthereumChain)
  nativeSymbol?: string; // gas token symbol
  note?: string;
  live?: boolean;
};

export const CHAINS: ChainBrand[] = [
  { slug: "arbitrum-sepolia", name: "Arbitrum", short: "ARB", color: "#28A0F0", logo: "/chains/arbitrum.png", family: "evm", chainId: 421614, explorer: "https://sepolia.arbiscan.io", rpc: "https://sepolia-rollup.arbitrum.io/rpc", nativeSymbol: "ETH", note: "verified on Arbiscan", live: true },
  { slug: "robinhood-testnet", name: "Robinhood Chain", short: "RH", color: "#00C805", logo: "/chains/robinhood.png", family: "evm", chainId: 46630, explorer: "https://explorer.testnet.chain.robinhood.com", rpc: "https://rpc.testnet.chain.robinhood.com", nativeSymbol: "ETH", note: "Arbitrum Orbit", live: true },
  { slug: "base-sepolia", name: "Base", short: "BASE", color: "#0052FF", logo: "/chains/base.png", family: "evm", chainId: 84532, explorer: "https://sepolia.basescan.org", rpc: "https://sepolia.base.org", nativeSymbol: "ETH", live: true },
  { slug: "arc-testnet", name: "Arc", short: "ARC", color: "#4B6BFB", logo: "/chains/arc.png", family: "evm", chainId: 5042002, explorer: "https://testnet.arcscan.app", rpc: "https://rpc.testnet.arc.network", nativeSymbol: "USDC", note: "Circle L1 · USDC gas", live: true },
  { slug: "avalanche-fuji", name: "Avalanche", short: "AVAX", color: "#E84142", logo: "/chains/avalanche.png", family: "evm", chainId: 43113, explorer: "https://testnet.snowtrace.io", rpc: "https://api.avax-test.network/ext/bc/C/rpc", nativeSymbol: "AVAX", live: true },
  { slug: "ethereum-sepolia", name: "Ethereum", short: "ETH", color: "#7B8CEA", logo: "/chains/ethereum.png", family: "evm", chainId: 11155111, explorer: "https://sepolia.etherscan.io", rpc: "https://ethereum-sepolia-rpc.publicnode.com", nativeSymbol: "ETH", live: true },
  { slug: "hedera-testnet", name: "Hedera", short: "ℏ", color: "#A78BFA", logo: "/chains/hedera.png", family: "hedera", chainId: 296, explorer: "https://hashscan.io/testnet", nativeSymbol: "HBAR", note: "non-EVM · HTS/HCS", live: true },
  { slug: "polygon-amoy", name: "Polygon", short: "POL", color: "#8247E5", logo: "/chains/polygon.png", family: "evm", chainId: 80002, explorer: "https://amoy.polygonscan.com", rpc: "https://rpc-amoy.polygon.technology", nativeSymbol: "POL", note: "Amoy testnet", live: true },
  // Solana devnet — Token-2022 permissioned RWA tokens. Full lifecycle verified
  // on devnet (issue/KYC/purchase/coupon/NAV/maturity, on-chain memo audit).
  { slug: "solana-devnet", name: "Solana", short: "SOL", color: "#14F195", logo: "/chains/solana.png", family: "solana", chainId: 103, explorer: "https://solscan.io", nativeSymbol: "SOL", note: "Token-2022 · devnet", live: true },
  // Sui testnet — Move closed-loop permissioned RWA tokens. Compliance is a
  // sui::token TokenPolicy + allowlist (KYC) rule; full lifecycle verified on-chain.
  { slug: "sui-testnet", name: "Sui", short: "SUI", color: "#4DA2FF", logo: "/chains/sui.png", family: "sui", explorer: "https://suiscan.xyz/testnet", nativeSymbol: "SUI", note: "Move · closed-loop token", live: true },
];

/** Solscan needs ?cluster=devnet/testnet for non-mainnet networks. */
function solanaCluster(chain: ChainBrand): string {
  if (chain.slug.includes("devnet")) return "?cluster=devnet";
  if (chain.slug.includes("testnet")) return "?cluster=testnet";
  return "";
}

export const LIVE_CHAINS = CHAINS.filter((c) => c.live);

export function chainBySlug(slug: string | null | undefined): ChainBrand | undefined {
  return CHAINS.find((c) => c.slug === slug);
}

/** Explorer URL for an address on a given chain (account/address page). */
export function explorerAddressUrl(chain: ChainBrand | undefined, address: string): string | null {
  if (!chain?.explorer || !address) return null;
  if (chain.family === "hedera") return `${chain.explorer}/account/${address}`;
  if (chain.family === "solana") return `${chain.explorer}/account/${address}${solanaCluster(chain)}`;
  if (chain.family === "sui") return `${chain.explorer}/account/${address}`;
  return `${chain.explorer}/address/${address}`;
}

/** Explorer URL for a token/contract on a given chain. */
export function explorerTokenUrl(chain: ChainBrand | undefined, token: string): string | null {
  if (!chain?.explorer || !token) return null;
  if (chain.family === "hedera") return `${chain.explorer}/token/${token}`;
  if (chain.family === "solana") return `${chain.explorer}/token/${token}${solanaCluster(chain)}`;
  // On Sui an asset is a shared object, not a coin type → /object.
  if (chain.family === "sui") return `${chain.explorer}/object/${token}`;
  return `${chain.explorer}/address/${token}`;
}

/** Explorer URL for a transaction hash on a given chain. */
export function explorerTxUrl(chain: ChainBrand | undefined, tx: string): string | null {
  if (!chain?.explorer || !tx || tx === "-") return null;
  if (chain.family === "hedera") return `${chain.explorer}/transaction/${tx}`;
  if (chain.family === "solana") return `${chain.explorer}/tx/${tx}${solanaCluster(chain)}`;
  if (chain.family === "sui") return `${chain.explorer}/tx/${tx}`; // digest, no 0x prefix
  const h = tx.startsWith("0x") ? tx : `0x${tx}`;
  return `${chain.explorer}/tx/${h}`;
}

/** Short, human-friendly explorer label per chain (e.g. "Arbiscan"). */
export function explorerName(chain: ChainBrand | undefined): string {
  if (!chain?.explorer) return "explorer";
  if (chain.family === "hedera") return "HashScan";
  if (chain.family === "solana") return "Solscan";
  try {
    const host = new URL(chain.explorer).hostname.replace(/^www\./, "");
    return host;
  } catch {
    return "explorer";
  }
}
