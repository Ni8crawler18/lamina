"""Solana chain adapter (non-EVM family) — Token-2022 permissioned RWA tokens.

This is a production-shaped implementation of the family-agnostic ``ChainAdapter``
on Solana. It is **disabled by default** (config/chains/solana-devnet.toml has
``enabled = false``) until verified against devnet with a funded operator keypair
— see the DEVNET VERIFICATION CHECKLIST at the bottom of this file.

Why Token-2022 (and not a memo/NFT hack)
----------------------------------------
RWAs need permissioned tokens: only KYC'd holders may ever hold or move them, and
the issuer must be able to claw back at maturity. Token-2022 ("Token Extensions")
provides exactly these primitives natively, giving ERC-3643-equivalent control
without a custom program for the token itself:

  • DefaultAccountState = Frozen   → every new token account is created FROZEN.
        A wallet cannot receive or transfer the asset until the issuer thaws its
        account. This is whitelist-by-default — the strongest compliance gate.
        KYC grant  = create the holder's ATA (frozen) + thaw it.
        KYC revoke = freeze the holder's ATA.
  • PermanentDelegate = operator   → the issuer is a permanent delegate on every
        account, so it can burn/transfer at maturity without the holder's
        signature. This backs force_redeem (maturity claw-back).
  • freeze_authority = operator    → freeze/unfreeze any holder (sanctions, KYC).

Settlement (coupons, principal) is paid in **USDC**, which on Solana is a legacy
SPL Token (not Token-2022); USDC transfers therefore use TOKEN_PROGRAM_ID.

Identity model
--------------
The backend operator keypair signs every transaction (same model as the EVM and
Hedera adapters). Holder ``holder_ref`` values are base58 owner pubkeys; the
adapter derives the associated token account (ATA) internally.

Audit trail
-----------
Each audit entry is written as an on-chain SPL Memo, tagged with the per-asset
audit anchor pubkey (a 0-lamport System transfer makes the anchor appear in the
transaction so it is queryable via getSignaturesForAddress). This is verifiable
on Solscan today. The documented production upgrade is a small Anchor program
exposing an append-only PDA log (gives true sequence numbers + cheap reads);
swapping it in touches only open_audit_topic/write_audit/read_audit here.

All solana/solders imports are lazy so this module loads even where those
packages are not installed — the adapter is only constructed when the Solana
chain is enabled in the registry.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.chains.base import AuditEntry, ChainAdapter, ChainConfig, TokenDeployment
from app.config import get_settings

logger = logging.getLogger(__name__)

# SPL Memo program (stable, deployed on every cluster).
_MEMO_PROGRAM_ID = "MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr"

# Token-2022 mint sizing with the PermanentDelegate + DefaultAccountState
# extensions. Mints and token accounts share a 165-byte base layout; an extended
# mint then has a 1-byte account-type discriminator followed by TLV entries
# (2-byte type + 2-byte length + data). PermanentDelegate data = 32, DAS data = 1.
#   size = 165 + 1 + (4 + 32) + (4 + 1) = 207
_MINT_WITH_EXT_SIZE = 207

# USDC has 6 decimals on every cluster.
_USDC_DECIMALS = 6


class SolanaAdapter(ChainAdapter):
    def __init__(self, config: ChainConfig):
        super().__init__(config)
        self._settings = get_settings()
        self._client = None  # lazy solana RPC client
        self._kp = None      # lazy operator Keypair

    # ── lazy client / keypair ────────────────────────────────────────────────
    def _conn(self):
        if self._client is None:
            from solana.rpc.api import Client
            self._client = Client(self.config.rpc_url)
        return self._client

    def _operator(self):
        """Operator Keypair. Loaded from SOLANA_KEYPAIR_PATH (solana-keygen json
        array) or SOLANA_OPERATOR_KEY (base58 secret)."""
        if self._kp is None:
            from solders.keypair import Keypair
            s = self._settings
            if getattr(s, "solana_keypair_path", ""):
                raw = json.loads(open(s.solana_keypair_path).read())
                self._kp = Keypair.from_bytes(bytes(raw))
            elif getattr(s, "solana_operator_key", ""):
                self._kp = Keypair.from_base58_string(s.solana_operator_key)
            else:
                raise ValueError(
                    "Solana operator key not configured "
                    "(set SOLANA_KEYPAIR_PATH or SOLANA_OPERATOR_KEY)"
                )
        return self._kp

    def _pubkey(self, s: str):
        from solders.pubkey import Pubkey
        return Pubkey.from_string(s)

    def _token_2022(self):
        from spl.token.constants import TOKEN_2022_PROGRAM_ID
        return TOKEN_2022_PROGRAM_ID

    def _token_legacy(self):
        from spl.token.constants import TOKEN_PROGRAM_ID
        return TOKEN_PROGRAM_ID

    # ── transaction send ─────────────────────────────────────────────────────
    def _send(self, instructions, extra_signers=()) -> str:
        """Compile, sign (operator + any extra signers), send and confirm.

        Preflight is skipped on purpose: public RPC nodes lag, so simulating
        against a stale node fails for txs that reference very recently created
        accounts (e.g. an ATA created in the previous request). Submitting
        directly lets the leader execute against real cluster state; we then read
        the signature status and raise on any on-chain error.
        """
        from solders.message import MessageV0
        from solders.transaction import VersionedTransaction
        from solana.rpc.commitment import Confirmed
        from solana.rpc.types import TxOpts

        client = self._conn()
        payer = self._operator()
        bh = client.get_latest_blockhash().value.blockhash
        msg = MessageV0.try_compile(payer.pubkey(), list(instructions), [], bh)
        tx = VersionedTransaction(msg, [payer, *extra_signers])
        sig = client.send_transaction(
            tx, opts=TxOpts(skip_preflight=True, preflight_commitment=Confirmed)
        ).value
        client.confirm_transaction(sig, commitment=Confirmed)
        status = client.get_signature_statuses([sig], search_transaction_history=True).value[0]
        if status and status.err is not None:
            raise RuntimeError(f"[solana] tx {sig} failed on-chain: {status.err}")
        return str(sig)

    def _ata(self, owner: str, mint: str, *, token_2022: bool = True):
        """Associated token account address for (owner, mint)."""
        from spl.token.instructions import get_associated_token_address
        prog = self._token_2022() if token_2022 else self._token_legacy()
        return get_associated_token_address(
            self._pubkey(owner), self._pubkey(mint), token_program_id=prog
        )

    def _ix_create_ata_idempotent(self, owner: str, mint: str, *, token_2022: bool = True):
        """Idempotent ATA-create instruction — a no-op if the ATA already exists,
        so it is race-free (no get_account_info pre-check needed)."""
        from spl.token.instructions import create_idempotent_associated_token_account
        prog = self._token_2022() if token_2022 else self._token_legacy()
        return create_idempotent_associated_token_account(
            payer=self._operator().pubkey(), owner=self._pubkey(owner),
            mint=self._pubkey(mint), token_program_id=prog,
        )

    # ── extension instruction builders (Token-2022) ──────────────────────────
    def _ix_init_permanent_delegate(self, mint, delegate):
        """InitializePermanentDelegate (TokenInstruction discriminant 35)."""
        from solders.instruction import AccountMeta, Instruction
        data = bytes([35]) + bytes(delegate)
        return Instruction(
            program_id=self._token_2022(),
            accounts=[AccountMeta(pubkey=mint, is_signer=False, is_writable=True)],
            data=data,
        )

    def _ix_init_default_account_state_frozen(self, mint):
        """DefaultAccountStateExtension::Initialize(Frozen).
        Outer discriminant 28, sub-instruction 0 (Initialize), state 2 (Frozen)."""
        from solders.instruction import AccountMeta, Instruction
        data = bytes([28, 0, 2])
        return Instruction(
            program_id=self._token_2022(),
            accounts=[AccountMeta(pubkey=mint, is_signer=False, is_writable=True)],
            data=data,
        )

    def _ix_memo(self, payload: str):
        from solders.instruction import Instruction
        return Instruction(
            program_id=self._pubkey(_MEMO_PROGRAM_ID),
            accounts=[],
            data=payload.encode("utf-8"),
        )

    # ── identity / explorer ──────────────────────────────────────────────────
    def operator_ref(self) -> str:
        return str(self._operator().pubkey())

    def _cluster_suffix(self) -> str:
        # Solscan needs ?cluster=devnet/testnet for non-mainnet networks.
        slug = self.config.slug
        if "devnet" in slug:
            return "?cluster=devnet"
        if "testnet" in slug:
            return "?cluster=testnet"
        return ""

    def explorer_tx(self, tx_ref: str) -> str:
        return f"{self.config.explorer_url}/tx/{tx_ref}{self._cluster_suffix()}"

    def explorer_address(self, ref: str) -> str:
        return f"{self.config.explorer_url}/account/{ref}{self._cluster_suffix()}"

    # ── token lifecycle ──────────────────────────────────────────────────────
    def deploy_asset_token(
        self, name: str, symbol: str, decimals: int, initial_supply: int,
        asset_type: str, jurisdiction: str,
    ) -> TokenDeployment:
        from solders.keypair import Keypair
        from solders.system_program import CreateAccountParams, create_account
        from spl.token.instructions import (
            InitializeMint2Params, MintToCheckedParams, ThawAccountParams,
            create_associated_token_account, initialize_mint2, mint_to_checked,
            thaw_account,
        )

        client = self._conn()
        operator = self._operator()
        op = operator.pubkey()
        mint_kp = Keypair()
        mint = mint_kp.pubkey()
        prog = self._token_2022()
        rent = client.get_minimum_balance_for_rent_exemption(_MINT_WITH_EXT_SIZE).value

        # Do it all in ONE atomic transaction: create the mint + init extensions
        # (which MUST precede InitializeMint2) + create the treasury ATA (created
        # frozen by DefaultAccountState) + thaw it + mint the full supply. A single
        # tx avoids any cross-transaction RPC-propagation race on the new mint.
        ixs = [
            create_account(CreateAccountParams(
                from_pubkey=op, to_pubkey=mint,
                lamports=rent, space=_MINT_WITH_EXT_SIZE, owner=prog,
            )),
            self._ix_init_permanent_delegate(mint, op),
            self._ix_init_default_account_state_frozen(mint),
            initialize_mint2(InitializeMint2Params(
                program_id=prog, mint=mint, decimals=decimals,
                mint_authority=op, freeze_authority=op,
            )),
        ]
        if initial_supply > 0:
            ata = self._ata(str(op), str(mint))
            ixs += [
                create_associated_token_account(
                    payer=op, owner=op, mint=mint, token_program_id=prog,
                ),
                thaw_account(ThawAccountParams(
                    program_id=prog, account=ata, mint=mint, authority=op,
                )),
                mint_to_checked(MintToCheckedParams(
                    program_id=prog, mint=mint, dest=ata, mint_authority=op,
                    amount=initial_supply, decimals=decimals,
                )),
            ]
        self._send(ixs, extra_signers=[mint_kp])

        # Per-asset audit anchor (queryable pubkey tag for the memo log).
        audit_anchor = str(Keypair().pubkey())
        try:
            self.write_audit(audit_anchor, "lifecycle", "asset_issued", {
                "name": name, "symbol": symbol, "token_ref": str(mint),
                "asset_type": asset_type, "jurisdiction": jurisdiction,
                "initial_supply": initial_supply,
            })
        except Exception as e:  # audit must not block issuance
            logger.warning("[solana] initial audit write failed: %s", e)

        logger.info("[solana] deployed %s mint=%s audit=%s", symbol, mint, audit_anchor)
        return TokenDeployment(token_ref=str(mint), audit_topic_ref=audit_anchor)

    def _mint_to_treasury(self, token_ref: str, amount: int, decimals: int) -> str:
        """Mint more supply to the treasury. The treasury ATA was created and
        thawed at issuance, so an idempotent create here is a no-op."""
        from spl.token.instructions import MintToCheckedParams, mint_to_checked
        operator = self._operator()
        ata = self._ata(self.operator_ref(), token_ref)
        return self._send([
            self._ix_create_ata_idempotent(self.operator_ref(), token_ref),
            mint_to_checked(MintToCheckedParams(
                program_id=self._token_2022(), mint=self._pubkey(token_ref), dest=ata,
                mint_authority=operator.pubkey(), amount=amount, decimals=decimals,
            )),
        ])

    def _decimals(self, token_ref: str) -> int:
        return int(self._conn().get_token_supply(self._pubkey(token_ref)).value.decimals)

    def mint(self, token_ref: str, amount: int) -> str:
        return self._mint_to_treasury(token_ref, amount, self._decimals(token_ref))

    def burn(self, token_ref: str, amount: int) -> str:
        from spl.token.instructions import BurnCheckedParams, burn_checked
        operator = self._operator()
        ata = self._ata(self.operator_ref(), token_ref)
        return self._send([burn_checked(BurnCheckedParams(
            program_id=self._token_2022(), mint=self._pubkey(token_ref), account=ata,
            owner=operator.pubkey(), amount=amount, decimals=self._decimals(token_ref),
        ))])

    def transfer_token(self, token_ref: str, to_ref: str, amount: int) -> str:
        from spl.token.instructions import TransferCheckedParams, transfer_checked
        operator = self._operator()
        decimals = self._decimals(token_ref)
        src = self._ata(self.operator_ref(), token_ref)
        dst = self._ata(to_ref, token_ref)
        # Idempotent create: a KYC'd holder's ATA already exists (thawed), so this
        # is a no-op. A non-KYC'd holder's ATA would be created FROZEN and the
        # transfer would (correctly) fail — compliance enforced by the token.
        return self._send([
            self._ix_create_ata_idempotent(to_ref, token_ref),
            transfer_checked(TransferCheckedParams(
                program_id=self._token_2022(), source=src, mint=self._pubkey(token_ref),
                dest=dst, owner=operator.pubkey(), amount=amount, decimals=decimals,
            )),
        ])

    def force_redeem(self, token_ref: str, holder_ref: str, amount: int) -> str:
        """Maturity claw-back: burn from the holder's account using the operator's
        PermanentDelegate authority (no holder signature required)."""
        from spl.token.instructions import BurnCheckedParams, burn_checked
        operator = self._operator()
        ata = self._ata(holder_ref, token_ref)
        return self._send([burn_checked(BurnCheckedParams(
            program_id=self._token_2022(), mint=self._pubkey(token_ref), account=ata,
            owner=operator.pubkey(), amount=amount, decimals=self._decimals(token_ref),
        ))])

    def token_balance(self, token_ref: str, holder_ref: str) -> int:
        ata = self._ata(holder_ref, token_ref)
        try:
            return int(self._conn().get_token_account_balance(ata).value.amount)
        except Exception:
            return 0  # ATA does not exist yet

    # ── compliance ───────────────────────────────────────────────────────────
    def grant_kyc(self, token_ref: str, holder_ref: str) -> str:
        """Whitelist a holder: ensure their ATA exists, then thaw it so they may
        receive/hold the asset (accounts are frozen-by-default)."""
        from spl.token.instructions import ThawAccountParams, thaw_account
        operator = self._operator()
        ata = self._ata(holder_ref, token_ref)
        return self._send([
            self._ix_create_ata_idempotent(holder_ref, token_ref),
            thaw_account(ThawAccountParams(
                program_id=self._token_2022(), account=ata,
                mint=self._pubkey(token_ref), authority=operator.pubkey(),
            )),
        ])

    def revoke_kyc(self, token_ref: str, holder_ref: str) -> str:
        return self.freeze(token_ref, holder_ref)

    def freeze(self, token_ref: str, holder_ref: str) -> str:
        from spl.token.instructions import FreezeAccountParams, freeze_account
        operator = self._operator()
        ata = self._ata(holder_ref, token_ref)
        return self._send([freeze_account(FreezeAccountParams(
            program_id=self._token_2022(), account=ata,
            mint=self._pubkey(token_ref), authority=operator.pubkey(),
        ))])

    def unfreeze(self, token_ref: str, holder_ref: str) -> str:
        from spl.token.instructions import ThawAccountParams, thaw_account
        operator = self._operator()
        ata = self._ata(holder_ref, token_ref)
        return self._send([thaw_account(ThawAccountParams(
            program_id=self._token_2022(), account=ata,
            mint=self._pubkey(token_ref), authority=operator.pubkey(),
        ))])

    # ── payouts (USDC = legacy SPL Token) ────────────────────────────────────
    def pay_stable(self, to_ref: str, amount_units: int) -> str:
        from spl.token.instructions import TransferCheckedParams, transfer_checked
        operator = self._operator()
        prog = self._token_legacy()
        usdc = self.config.contract("usdc")
        src = self._ata(self.operator_ref(), usdc, token_2022=False)
        dst = self._ata(to_ref, usdc, token_2022=False)
        # Legacy SPL USDC has no frozen-by-default; idempotent create is a no-op
        # if the recipient already holds USDC, else it opens their USDC account.
        return self._send([
            self._ix_create_ata_idempotent(to_ref, usdc, token_2022=False),
            transfer_checked(TransferCheckedParams(
                program_id=prog, source=src, mint=self._pubkey(usdc), dest=dst,
                owner=operator.pubkey(), amount=amount_units, decimals=_USDC_DECIMALS,
            )),
        ])

    def pay_native(self, to_ref: str, amount_wei: int) -> str:
        """Native SOL transfer. ``amount_wei`` is lamports (SOL's smallest unit)."""
        from solders.system_program import TransferParams, transfer
        return self._send([transfer(TransferParams(
            from_pubkey=self._operator().pubkey(),
            to_pubkey=self._pubkey(to_ref), lamports=amount_wei,
        ))])

    def stable_balance(self, holder_ref: str) -> int:
        ata = self._ata(holder_ref, self.config.contract("usdc"), token_2022=False)
        try:
            return int(self._conn().get_token_account_balance(ata).value.amount)
        except Exception:
            return 0

    # ── audit (SPL Memo, tagged by anchor pubkey) ────────────────────────────
    def open_audit_topic(self, memo: str) -> str:
        from solders.keypair import Keypair
        return str(Keypair().pubkey())

    def write_audit(self, topic_ref: str, agent: str, action: str, details: dict) -> int:
        """Write one audit entry as an on-chain memo, tagged with the topic anchor
        so it is queryable via getSignaturesForAddress(topic_ref)."""
        from solders.system_program import TransferParams, transfer
        payload = json.dumps({
            "agent": agent, "action": action, "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # 0-lamport self/anchor transfer makes the anchor appear in the tx (so it
        # is indexed for the address), alongside the memo carrying the payload.
        tag = transfer(TransferParams(
            from_pubkey=self._operator().pubkey(),
            to_pubkey=self._pubkey(topic_ref), lamports=0,
        ))
        self._send([tag, self._ix_memo(payload)])
        return 0  # sequence is assigned at read time (see read_audit)

    def read_audit(self, topic_ref: str, limit: int = 100) -> list[AuditEntry]:
        client = self._conn()
        try:
            sigs = client.get_signatures_for_address(
                self._pubkey(topic_ref), limit=limit
            ).value
        except Exception as e:
            logger.error("[solana] read_audit signatures failed for %s: %s", topic_ref, e)
            return []

        out: list[AuditEntry] = []
        # signatures come newest-first; reverse to ascending for stable sequencing
        for i, info in enumerate(reversed(list(sigs))):
            memo = self._extract_memo(str(info.signature))
            if memo is None:
                continue
            try:
                content = json.loads(memo)
            except json.JSONDecodeError:
                content = {"raw": memo}
            ts = content.get("timestamp", "")
            if not ts and getattr(info, "block_time", None):
                ts = datetime.fromtimestamp(info.block_time, tz=timezone.utc).isoformat()
            out.append(AuditEntry(
                sequence=i,
                timestamp=ts,
                agent=content.get("agent", ""),
                action=content.get("action", ""),
                details=content.get("details", content),
            ))
        return out

    def _extract_memo(self, signature: str) -> str | None:
        """Pull the memo text out of a confirmed transaction's program logs."""
        from solders.signature import Signature
        try:
            tx = self._conn().get_transaction(
                Signature.from_string(signature), max_supported_transaction_version=0
            ).value
        except Exception:
            return None
        logs = (tx and tx.transaction and tx.transaction.meta
                and tx.transaction.meta.log_messages) or []
        for line in logs:
            # Memo program logs: Program log: Memo (len N): "<text>" — the inner
            # text is debug-escaped, so unescape \" and \\ before returning.
            marker = 'Memo (len'
            if marker in line and '"' in line:
                text = line[line.index('"') + 1: line.rindex('"')]
                return text.replace('\\"', '"').replace('\\\\', '\\')
        return None

    # ── helpers (not part of the interface) ──────────────────────────────────
    @staticmethod
    def new_wallet() -> tuple[str, str]:
        """Generate a Solana keypair. Returns (pubkey_base58, secret_base58)."""
        from solders.keypair import Keypair
        kp = Keypair()
        return str(kp.pubkey()), kp.to_base58_string()


# ── DEVNET VERIFICATION CHECKLIST (flip enabled=true only after these pass) ───
# 1. pip install -r requirements.txt  (adds solana + solders)
# 2. Fund the operator keypair with devnet SOL: `solana airdrop 2 <pubkey> --url devnet`
#    and devnet USDC from Circle's faucet (https://faucet.circle.com).
# 3. Set SOLANA_KEYPAIR_PATH or SOLANA_OPERATOR_KEY in server/.env.
# 4. Confirm _MINT_WITH_EXT_SIZE (207) matches the on-chain rent-exempt size for a
#    mint with PermanentDelegate + DefaultAccountState (the create_account will
#    fail loudly if wrong).
# 5. Run the full lifecycle: issue → grant_kyc → transfer/purchase → coupon (USDC)
#    → update-nav → mature, and verify each on Solscan (?cluster=devnet).
# 6. Then set enabled = true in config/chains/solana-devnet.toml and add the chain
#    to the frontend's LIVE_CHAINS (client/src/lib/chains.ts: live: true).
