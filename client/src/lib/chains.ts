// Chains Lamina deploys to. Logos are recolored to a cohesive blue monochrome
// (see /public/chains/*.png) so the set reads as one enterprise system.
export type ChainBrand = {
  slug: string;
  name: string;
  short: string;
  color: string;
  logo: string;
  family: "evm" | "hedera";
  chainId?: number; // EVM numeric chain id (for MetaMask network switching)
  explorer?: string; // block explorer base url
  note?: string;
  live?: boolean;
};

export const CHAINS: ChainBrand[] = [
  { slug: "arbitrum-sepolia", name: "Arbitrum", short: "ARB", color: "#28A0F0", logo: "/chains/arbitrum.png", family: "evm", chainId: 421614, explorer: "https://sepolia.arbiscan.io", note: "verified on Arbiscan", live: true },
  { slug: "robinhood-testnet", name: "Robinhood Chain", short: "RH", color: "#00C805", logo: "/chains/robinhood.png", family: "evm", chainId: 46630, explorer: "https://explorer.testnet.chain.robinhood.com", note: "Arbitrum Orbit", live: true },
  { slug: "base-sepolia", name: "Base", short: "BASE", color: "#0052FF", logo: "/chains/base.png", family: "evm", chainId: 84532, explorer: "https://sepolia.basescan.org", live: true },
  { slug: "arc-testnet", name: "Arc", short: "ARC", color: "#4B6BFB", logo: "/chains/arc.png", family: "evm", chainId: 5042002, explorer: "https://testnet.arcscan.app", note: "Circle L1 · USDC gas", live: true },
  { slug: "avalanche-fuji", name: "Avalanche", short: "AVAX", color: "#E84142", logo: "/chains/avalanche.png", family: "evm", chainId: 43113, explorer: "https://testnet.snowtrace.io", live: true },
  { slug: "ethereum-sepolia", name: "Ethereum", short: "ETH", color: "#7B8CEA", logo: "/chains/ethereum.png", family: "evm", chainId: 11155111, explorer: "https://sepolia.etherscan.io", live: true },
  { slug: "hedera-testnet", name: "Hedera", short: "ℏ", color: "#A78BFA", logo: "/chains/hedera.png", family: "hedera", chainId: 296, explorer: "https://hashscan.io/testnet", note: "non-EVM · HTS/HCS", live: true },
  { slug: "polygon-amoy", name: "Polygon", short: "POL", color: "#8247E5", logo: "/chains/polygon.png", family: "evm", chainId: 80002, explorer: "https://amoy.polygonscan.com", note: "Amoy testnet", live: true },
];

export const LIVE_CHAINS = CHAINS.filter((c) => c.live);

export function chainBySlug(slug: string | null | undefined): ChainBrand | undefined {
  return CHAINS.find((c) => c.slug === slug);
}

/** Explorer URL for an address on a given chain (account/address page). */
export function explorerAddressUrl(chain: ChainBrand | undefined, address: string): string | null {
  if (!chain?.explorer || !address) return null;
  if (chain.family === "hedera") return `${chain.explorer}/account/${address}`;
  return `${chain.explorer}/address/${address}`;
}
