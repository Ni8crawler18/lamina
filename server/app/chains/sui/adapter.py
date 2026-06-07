"""Sui chain adapter (non-EVM family) — Move closed-loop permissioned RWA tokens.

A production-shaped implementation of the family-agnostic ``ChainAdapter`` on Sui,
backed by the ``lamina_rwa`` Move package (contracts-sui/). It mirrors the EVM and
Hedera adapters' model exactly: the backend operator key signs every transaction
and holds the capability objects; investor wallets are identity only.

Why this shape (vs. the EVM contracts)
--------------------------------------
Sui has no per-asset "deploy a contract" primitive, and a closed-loop currency's
type is fixed at publish time (one-time witness). So instead of a fresh token type
per asset, ONE closed-loop currency ``RWA`` is published whose ``TokenPolicy`` +
allowlist (KYC) rule are the shared compliance engine, and each issued asset is a
shared ``Asset`` ledger object. Compliance is enforced at the type level: the same
policy allowlist that gates the closed-loop standard's own ``confirm_request`` is
what every ledger transfer checks — KYC/freeze cannot be bypassed.

  * token_ref      = the asset's shared ``Asset`` object id
  * holder_ref     = a base-format Sui address (0x…)
  * tx_ref         = a transaction digest
  * audit topic    = the asset's shared ``AuditLog`` object id; entries are
                     ``AuditRecord`` events, queried back by log id.

Settlement (coupons, principal) pays Circle USDC — a normal ``Coin<USDC>`` — via a
split+transfer PTB. Native payouts split from the gas coin.

All pysui imports are lazy so this module loads even where pysui is not installed;
the adapter is only constructed when the Sui chain is enabled in the registry.
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timezone

from app.chains.base import AuditEntry, ChainAdapter, ChainConfig, TokenDeployment
from app.config import get_settings

logger = logging.getLogger(__name__)

# Default gas budget (MIST) — a generous ceiling; actual charge is far smaller.
_GAS_BUDGET = "200000000"  # 0.2 SUI
_USDC_DECIMALS = 6


class SuiAdapter(ChainAdapter):
    def __init__(self, config: ChainConfig):
        super().__init__(config)
        self._settings = get_settings()
        self._cfg = None  # lazy SuiConfig
        self._client = None  # lazy SyncClient

    # ── lazy client ───────────────────────────────────────────────────────────
    def _conn(self):
        if self._client is None:
            from pysui import SuiConfig, SyncClient

            key = self._settings.sui_operator_key
            if not key:
                raise ValueError("Sui operator key not configured (set SUI_OPERATOR_KEY)")
            # pysui 0.84 emits GraphQL-migration deprecation warnings on the stable
            # JSON-RPC client; silence them — JSON-RPC is the supported path here.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                self._cfg = SuiConfig.user_config(rpc_url=self.config.rpc_url, prv_keys=[key])
                self._client = SyncClient(self._cfg)
        return self._client

    def _txn(self):
        from pysui.sui.sui_txn import SyncTransaction

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return SyncTransaction(client=self._conn())

    # -- pure / object argument helpers ----------------------------------------
    @staticmethod
    def _u8(v: int):
        from pysui.sui.sui_types.scalars import SuiU8

        return SuiU8(v)

    @staticmethod
    def _u64(v: int):
        from pysui.sui.sui_types.scalars import SuiU64

        return SuiU64(int(v))

    @staticmethod
    def _str(v: str):
        from pysui.sui.sui_types.scalars import SuiString

        return SuiString(v)

    @staticmethod
    def _addr(v: str):
        from pysui.sui.sui_types.address import SuiAddress

        return SuiAddress(v)

    @staticmethod
    def _obj(v: str):
        from pysui import ObjectID

        return ObjectID(v)

    def _target(self, module: str, fn: str) -> str:
        return f"{self.config.contract('package')}::{module}::{fn}"

    # -- execution -------------------------------------------------------------
    def _execute(self, txn) -> str:
        """Run a built transaction, assert success, return the digest."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            res = txn.execute(gas_budget=_GAS_BUDGET)
        if not res.is_ok():
            raise RuntimeError(f"[sui] tx failed: {res.result_string}")
        data = res.result_data
        status = data.effects.status.status
        if status != "success":
            raise RuntimeError(f"[sui] tx {data.digest} reverted: {data.effects.status}")
        return data.digest

    def _move_call(self, module: str, fn: str, arguments: list, type_arguments=None) -> str:
        txn = self._txn()
        txn.move_call(
            target=self._target(module, fn),
            arguments=arguments,
            type_arguments=type_arguments or [],
        )
        return self._execute(txn)

    # ── identity / explorer ────────────────────────────────────────────────────
    def operator_ref(self) -> str:
        return str(self._conn().config.active_address)

    def explorer_tx(self, tx_ref: str) -> str:
        return f"{self.config.explorer_url}/tx/{tx_ref}"

    def explorer_address(self, ref: str) -> str:
        # Suiscan resolves both object ids and account addresses under /object and
        # /account; objects (token/policy refs) are the common case for reports.
        return f"{self.config.explorer_url}/object/{ref}"

    # ── token lifecycle ─────────────────────────────────────────────────────────
    def deploy_asset_token(
        self,
        name: str,
        symbol: str,
        decimals: int,
        initial_supply: int,
        asset_type: str,
        jurisdiction: str,
    ) -> TokenDeployment:
        """Issue an asset: one tx creates the shared Asset ledger + its AuditLog.
        The created object ids are read back from the tx effects."""
        txn = self._txn()
        txn.move_call(
            target=self._target("rwa", "issue_asset"),
            arguments=[
                self._obj(self.config.contract("operator_cap")),
                self._str(name),
                self._str(symbol),
                self._u8(decimals),
                self._u64(initial_supply),
                self._str(asset_type),
                self._str(jurisdiction),
                self._str(""),  # issuer (legal name held in DB)
            ],
            type_arguments=[],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            res = txn.execute(gas_budget=_GAS_BUDGET)
        if not res.is_ok():
            raise RuntimeError(f"[sui] issue_asset failed: {res.result_string}")
        data = res.result_data
        if data.effects.status.status != "success":
            raise RuntimeError(f"[sui] issue_asset reverted: {data.effects.status}")

        token_ref = audit_ref = ""
        for change in data.object_changes:
            otype = change.get("objectType", "") if isinstance(change, dict) else ""
            if change.get("type") != "created":
                continue
            if otype.endswith("::rwa::Asset"):
                token_ref = change.get("objectId", "")
            elif otype.endswith("::audit::AuditLog"):
                audit_ref = change.get("objectId", "")
        if not token_ref or not audit_ref:
            raise RuntimeError(f"[sui] issue_asset created objects missing in {data.digest}")
        logger.info("[sui] issued %s asset=%s audit=%s", symbol, token_ref, audit_ref)
        return TokenDeployment(token_ref=token_ref, audit_topic_ref=audit_ref)

    def mint(self, token_ref: str, amount: int) -> str:
        return self._move_call(
            "rwa",
            "mint",
            [
                self._obj(self.config.contract("operator_cap")),
                self._obj(token_ref),
                self._u64(amount),
            ],
        )

    def burn(self, token_ref: str, amount: int) -> str:
        return self._move_call(
            "rwa",
            "burn",
            [
                self._obj(self.config.contract("operator_cap")),
                self._obj(token_ref),
                self._u64(amount),
            ],
        )

    def transfer_token(self, token_ref: str, to_ref: str, amount: int) -> str:
        return self._move_call(
            "rwa",
            "transfer",
            [
                self._obj(self.config.contract("operator_cap")),
                self._obj(self.config.contract("policy")),
                self._obj(token_ref),
                self._addr(to_ref),
                self._u64(amount),
            ],
        )

    def force_redeem(self, token_ref: str, holder_ref: str, amount: int) -> str:
        return self._move_call(
            "rwa",
            "force_redeem",
            [
                self._obj(self.config.contract("operator_cap")),
                self._obj(token_ref),
                self._addr(holder_ref),
                self._u64(amount),
            ],
        )

    def token_balance(self, token_ref: str, holder_ref: str) -> int:
        return self._dev_inspect_u64(
            "rwa",
            "balance_of",
            [
                self._obj(token_ref),
                self._addr(holder_ref),
            ],
        )

    # ── compliance (KYC/freeze live in the shared TokenPolicy allowlist) ────────
    def grant_kyc(self, token_ref: str, holder_ref: str) -> str:
        return self._policy_call("grant_kyc", holder_ref)

    def revoke_kyc(self, token_ref: str, holder_ref: str) -> str:
        return self._policy_call("revoke_kyc", holder_ref)

    def freeze(self, token_ref: str, holder_ref: str) -> str:
        return self._policy_call("freeze_holder", holder_ref)

    def unfreeze(self, token_ref: str, holder_ref: str) -> str:
        return self._policy_call("unfreeze_holder", holder_ref)

    def _policy_call(self, fn: str, holder_ref: str) -> str:
        """KYC/freeze act on the global TokenPolicy allowlist (investor-level), so
        token_ref is not needed on chain — compliance is one source of truth."""
        return self._move_call(
            "rwa",
            fn,
            [
                self._obj(self.config.contract("operator_cap")),
                self._obj(self.config.contract("policy")),
                self._obj(self.config.contract("policy_cap")),
                self._addr(holder_ref),
            ],
        )

    # ── payouts ──────────────────────────────────────────────────────────────
    def pay_stable(self, to_ref: str, amount_units: int) -> str:
        """Pay USDC: gather the operator's USDC coins, merge into one, split off
        `amount_units` and transfer to the recipient — all in one PTB."""
        client = self._conn()
        usdc = self.config.contract("usdc")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            coins_res = client.get_coin(
                coin_type=self._str(usdc),
                address=self._addr(self.operator_ref()),
                fetch_all=True,
            )
        if not coins_res.is_ok():
            raise RuntimeError(f"[sui] get USDC coins failed: {coins_res.result_string}")
        coins = sorted(coins_res.result_data.data, key=lambda c: int(c.balance), reverse=True)
        if not coins:
            raise RuntimeError("[sui] operator holds no USDC")
        total = sum(int(c.balance) for c in coins)
        if total < amount_units:
            raise RuntimeError(f"[sui] insufficient USDC: have {total}, need {amount_units}")

        txn = self._txn()
        primary = self._obj(coins[0].coin_object_id)
        if len(coins) > 1:
            txn.merge_coins(
                merge_to=primary,
                merge_from=[self._obj(c.coin_object_id) for c in coins[1:]],
            )
        split = txn.split_coin(coin=primary, amounts=[amount_units])
        txn.transfer_objects(transfers=[split], recipient=self._addr(to_ref))
        return self._execute(txn)

    def pay_native(self, to_ref: str, amount_wei: int) -> str:
        """Pay native SUI (`amount_wei` is MIST) — split from the gas coin."""
        txn = self._txn()
        split = txn.split_coin(coin=txn.gas, amounts=[amount_wei])
        txn.transfer_objects(transfers=[split], recipient=self._addr(to_ref))
        return self._execute(txn)

    def stable_balance(self, holder_ref: str) -> int:
        client = self._conn()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            res = client.get_coin(
                coin_type=self._str(self.config.contract("usdc")),
                address=self._addr(holder_ref),
                fetch_all=True,
            )
        if not res.is_ok():
            return 0
        return sum(int(c.balance) for c in res.result_data.data)

    # ── audit ──────────────────────────────────────────────────────────────────
    def open_audit_topic(self, memo: str) -> str:
        # On Sui the audit topic is created atomically inside issue_asset (and its
        # id returned as audit_topic_ref), so a standalone open is never used.
        raise NotImplementedError("Sui opens the audit topic atomically during deploy_asset_token")

    def write_audit(self, topic_ref: str, agent: str, action: str, details: dict) -> int:
        txn = self._txn()
        txn.move_call(
            target=self._target("rwa", "write_audit"),
            arguments=[
                self._obj(self.config.contract("operator_cap")),
                self._obj(topic_ref),
                self._str(agent),
                self._str(action),
                self._str(json.dumps(details, default=str)),
            ],
            type_arguments=[],
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            res = txn.execute(gas_budget=_GAS_BUDGET)
        if not res.is_ok():
            raise RuntimeError(f"[sui] write_audit failed: {res.result_string}")
        data = res.result_data
        if data.effects.status.status != "success":
            raise RuntimeError(f"[sui] write_audit reverted: {data.effects.status}")
        # Pull the sequence number straight from the emitted AuditRecord event.
        try:
            for ev in data.events or []:
                pj = getattr(ev, "parsed_json", None) or {}
                if "seq" in pj:
                    return int(pj["seq"])
        except Exception:
            pass
        return 0

    def read_audit(self, topic_ref: str, limit: int = 100) -> list[AuditEntry]:
        from pysui.sui.sui_builders.get_builders import QueryEvents
        from pysui.sui.sui_types.event_filter import MoveEventTypeQuery
        from pysui.sui.sui_types.scalars import SuiBoolean, SuiInteger

        client = self._conn()
        event_type = f"{self.config.contract('package')}::audit::AuditRecord"
        records: list[AuditEntry] = []
        cursor = None
        try:
            # AuditRecord is shared across all assets, so fetch by type and filter
            # to this topic. Page until we have enough for this log or run out.
            for _ in range(10):  # safety bound on pagination
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", DeprecationWarning)
                    builder = QueryEvents(
                        query=MoveEventTypeQuery(event_type),
                        cursor=cursor,
                        limit=SuiInteger(50),
                        descending_order=SuiBoolean(False),
                    )
                    res = client.execute(builder)
                if not res.is_ok():
                    logger.error("[sui] read_audit query failed: %s", res.result_string)
                    break
                env = res.result_data
                for ev in env.data:
                    pj = getattr(ev, "parsed_json", None) or {}
                    if pj.get("log") != topic_ref:
                        continue
                    ts_ms = getattr(ev, "timestamp_ms", None) or 0
                    ts = (
                        datetime.fromtimestamp(int(ts_ms) / 1000, tz=timezone.utc).isoformat()
                        if ts_ms
                        else ""
                    )
                    details = pj.get("details", "")
                    try:
                        details = json.loads(details) if isinstance(details, str) else details
                    except json.JSONDecodeError:
                        details = {"raw": details}
                    records.append(
                        AuditEntry(
                            sequence=int(pj.get("seq", len(records))),
                            timestamp=ts,
                            agent=pj.get("agent", ""),
                            action=pj.get("action", ""),
                            details=details if isinstance(details, dict) else {"value": details},
                        )
                    )
                if not getattr(env, "has_next_page", False):
                    break
                cursor = env.next_cursor
        except Exception as e:
            logger.error("[sui] read_audit error for %s: %s", topic_ref, e)
        records.sort(key=lambda r: r.sequence)
        return records[:limit]

    # ── reads via devInspect ────────────────────────────────────────────────────
    def _dev_inspect_u64(self, module: str, fn: str, arguments: list) -> int:
        """Call a view function via devInspectTransactionBlock and decode a u64."""
        try:
            txn = self._txn()
            txn.move_call(
                target=self._target(module, fn),
                arguments=arguments,
                type_arguments=[],
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                res = txn.inspect_all()
            results = getattr(res, "results", None) or (
                res.get("results") if isinstance(res, dict) else None
            )
            if not results:
                return 0
            first = results[0]
            rv = (
                first.get("returnValues")
                if isinstance(first, dict)
                else getattr(first, "return_values", None)
            )
            if not rv:
                return 0
            raw = rv[0][0]  # [ [byte,...], "u64" ]
            return int.from_bytes(bytes(raw), "little")
        except Exception as e:
            logger.error("[sui] devInspect %s::%s failed: %s", module, fn, e)
            return 0

    # ── helpers (not part of the interface) ──────────────────────────────────
    @staticmethod
    def new_wallet() -> tuple[str, str]:
        """Generate a Sui ed25519 keypair. Returns (address, bech32_private_key)."""
        from pysui.abstracts.client_keypair import SignatureScheme
        from pysui.sui.sui_crypto import create_new_keypair

        _mnem, keypair = create_new_keypair(SignatureScheme.ED25519)
        addr = format(keypair.to_sui_address())
        return addr, keypair.serialize()
