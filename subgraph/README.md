# Laminaa subgraph

Indexes Laminaa's on-chain compliance and lifecycle trail directly from
contract events, no dependency on our own backend/Postgres. Anyone can query
every asset ever issued through `LaminaFactory`, its full `AuditLog` history
(issuance, KYC grants, transfer approvals, coupon distributions, NAV
updates, redemption), and every KYC/freeze/transfer event on the per-asset
`LaminaRWAToken`, over a public GraphQL API.

This covers the 7 EVM chains only (Arbitrum Sepolia, Robinhood Chain, Base
Sepolia, Arc, Avalanche Fuji, Ethereum Sepolia, Polygon Amoy) - subgraphs are
per-EVM-network by design, so Hedera/Solana/Sui stay out of scope here and
are covered instead by Laminaa's own Mirror Node / RPC reads.

## Deploy for a given chain

The schema and mapping are chain-agnostic; only `subgraph.yaml` changes.
`subgraph.yaml` in this folder is pre-filled for **Base Sepolia**. To target
another chain, copy it and swap `network` + both dataSource `address` values
(same contracts share addresses on 4 of the 7 chains, since they were
deployed by the same operator at the same nonce - see
`deployment_contract.txt` at the repo root for the full explanation):

| Chain             | network (Graph)   | LaminaFactory                                | AuditLog                                     |
|-------------------|--------------------|-----------------------------------------------|-----------------------------------------------|
| Arbitrum Sepolia   | `arbitrum-sepolia` | `0x8610E57f1357a41c2991ba64764c2Fdc8b2DD33e`  | `0x2721b95C0fF4756D71Ab6357A38C35e458627595`  |
| Robinhood Testnet  | `robinhood-testnet`| `0xd556c46758B2C4B62f929256dc3FA53fbd375A3A`  | `0x153786D589c1d3bddEa68f232269d47Cb110D6Cd`  |
| Base Sepolia       | `base-sepolia`     | `0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`  | `0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`  |
| Arc Testnet        | (check Graph's supported-network list; may need Firehose/substreams) | `0x45a36ea47577A4415cAc75256F78ccD66bC29E2c` | `0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7` |
| Avalanche Fuji     | `avalanche-fuji`   | `0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`  | `0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`  |
| Ethereum Sepolia   | `sepolia`          | `0x45a36ea47577A4415cAc75256F78ccD66bC29E2c`  | `0xca7f1c8BC559F0E20c3F12085A7Fa426397977f7`  |
| Polygon Amoy       | `polygon-amoy`     | `0xa96aAbCE0Ab4c9758B05D361d09A11144F3F6D6A`  | (same pattern - check deployment_contract.txt) |

Before deploying, set each dataSource's `startBlock` to the contract's real
deployment block (visible on that chain's explorer, linked in
`deployment_contract.txt`) instead of `0`, or the initial sync will replay
the entire chain history unnecessarily.

```bash
cd subgraph
npm install
npx graph codegen
npx graph build
# create the subgraph in Graph Studio first (one-time, via the UI or `graph init`),
# then, authenticated with your own Studio deploy key:
npx graph deploy --node https://api.studio.thegraph.com/deploy/ laminaa
```

Deploying requires your own Graph Studio account/API key - that's an
account-bound step, not something this scaffold can do for you.
