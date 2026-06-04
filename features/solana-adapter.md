# Solana Adapter (Token-2022 permissioned RWA tokens)

Status: **live on devnet, full lifecycle verified.** `config/chains/solana-devnet.toml`
→ `enabled = true`; frontend `live: true`. Operator keypair at `~/Laminaa-sol.json`
(`SOLANA_KEYPAIR_PATH`), funded with devnet SOL + Circle devnet USDC.

Verified end-to-end on devnet (sample run, asset "Solana Test Bond" / STB,
mint `4LzJYkEMCUFM1BSWWSjsAQgMZXGpULQnmQFTYTpJLdHG`):
issue → grant_kyc → purchase (`f9q4Dnm5…`) → coupon in USDC (`3CQxaDd8…`) →
update-nav → maturity (clawback wipe 500 + burn 99500 + 5 USDC principal) →
10-entry on-chain memo audit trail read back parsed. All verifiable on Solscan
(`?cluster=devnet`).

## Why this design is production-viable (not a demo hack)

RWAs require permissioned tokens: only KYC'd wallets may ever hold or move them,
and the issuer must claw back at maturity. Solana's **Token-2022** ("Token
Extensions") provides these natively — no custom token program needed:

| Requirement | Token-2022 primitive | Where in adapter |
|---|---|---|
| Whitelist-by-default | `DefaultAccountState = Frozen` (new accounts start frozen) | `deploy_asset_token` |
| KYC grant | create holder ATA (frozen) + `thaw_account` | `grant_kyc` |
| KYC revoke / sanctions | `freeze_account` | `revoke_kyc`, `freeze` |
| Maturity claw-back | `PermanentDelegate` (operator) → `burn_checked` without holder sig | `force_redeem` |
| Coupons / principal | USDC (legacy SPL Token) `transfer_checked` | `pay_stable` |
| Audit trail | on-chain SPL Memo tagged by per-asset anchor pubkey | `write/read_audit` |

`DefaultAccountState = Frozen` is the key: a non-KYC'd wallet **cannot receive or
transfer** the asset — equivalent to ERC-3643's transfer restriction, enforced by
the token program itself.

## What maps cleanly vs. what needs more

- **Clean (Token-2022 native):** issuance, mint, burn, transfer, balance, KYC
  grant/revoke, freeze/unfreeze, force-redeem, USDC settlement. No custom program.
- **Per-transfer programmatic rules** (e.g. jurisdiction logic, lock-ups enforced
  *on-chain* rather than in the backend compliance engine): would use a Token-2022
  **TransferHook** program (Anchor). The backend compliance engine already gates
  these off-chain before signing, so the scaffold is correct without it; the hook
  is the path to fully trustless on-chain enforcement.
- **Audit log:** scaffold uses SPL memos (verifiable on Solscan today). Production
  upgrade = a small Anchor program with an append-only PDA log → true sequence
  numbers + cheap reads. Swapping it touches only `open/write/read_audit` and the
  `audit_log` program id in the TOML.

## Architecture fit

Zero changes to `services/` — they depend only on `ChainAdapter`. Adding Solana
was: one adapter class, one TOML, a registry one-liner, settings for the operator
keypair, and frontend chain/explorer entries. This is the chain-agnostic thesis
working as designed.

## Files

- `app/chains/solana/adapter.py` — `SolanaAdapter` (sync, lazy imports, ~370 LOC)
- `config/chains/solana-devnet.toml` — devnet config, `enabled=false`
- `app/chains/registry.py` — `family == "solana"` branch
- `app/config.py` — `solana_keypair_path` / `solana_operator_key`
- `pyproject.toml` — optional `[solana]` deps (`solana`, `solders`)
- Frontend: `client/src/lib/chains.ts` — `solana` family + Solscan helpers +
  chain entry (`live:false`)

## To enable (devnet)

1. `pip install -e ".[solana]"` (server)
2. Fund operator keypair: `solana airdrop 2 <pubkey> --url devnet`; devnet USDC
   from https://faucet.circle.com
3. Set `SOLANA_KEYPAIR_PATH` (solana-keygen json) or `SOLANA_OPERATOR_KEY`
   (base58 secret) in `server/.env`
4. Run full lifecycle (issue → grant_kyc → purchase → coupon → nav → mature),
   verify each on Solscan (`?cluster=devnet`)
5. Add `client/public/chains/solana.png` (logo)
6. Flip `enabled = true` in the TOML **and** `live: true` in `chains.ts`

## Known checks before mainnet

- Confirm `_MINT_WITH_EXT_SIZE` (207) matches rent-exempt size for a mint with
  PermanentDelegate + DefaultAccountState (account creation fails loudly if off).
- Use a private RPC (Helius/Triton) via `RPC_URL_SOLANA_DEVNET` — the public
  endpoint rate-limits.
- Mainnet: fresh operator keypair / multisig (squads), never reuse testnet keys.
