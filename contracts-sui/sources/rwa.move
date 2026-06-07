/// Laminaa RWA — the Sui-native equivalent of LaminaRWAToken.sol + LaminaFactory.sol.
///
/// Design (why it looks different from the EVM contracts):
///   * Sui has no per-asset `new contract` primitive, and a closed-loop currency's
///     type is fixed at publish time (one-time witness). So instead of deploying a
///     fresh token type per asset, we publish ONE closed-loop currency `RWA` whose
///     `TokenPolicy` + allowlist rule are the shared compliance engine, and model
///     each issued asset as its own shared `Asset` object carrying an on-chain
///     balance ledger. This matches Laminaa's custodial identity model exactly: the
///     backend operator signs every action; investor wallets are identity only.
///   * The closed-loop standard does the compliance heavy-lifting: the ledger
///     `transfer` consults the SAME policy allowlist that gates the standard's own
///     `confirm_request` (see `settle_closed_loop`), so KYC/freeze is enforced at
///     the type level — one source of compliance truth, not a bypassable mapping.
///
/// Authority: the publisher (the backend operator) receives the `TreasuryCap`, the
/// `TokenPolicyCap`, and an `OperatorCap`. Every privileged entry requires the
/// `OperatorCap`, the on-chain mirror of "the backend holds the operator key and
/// signs every action". Value functions stay lean; the audit trail is written
/// explicitly by the services via `write_audit` (same split as the EVM adapter).
module lamina_rwa::rwa;

use std::string::String;
use sui::coin::{Self, TreasuryCap};
use sui::token::{Self, TokenPolicy, TokenPolicyCap};
use sui::table::{Self, Table};
use sui::event;
use lamina_rwa::audit::{Self, AuditLog};
use lamina_rwa::allowlist::{Self, Allowlist};

/// One-time witness for the closed-loop RWA currency.
public struct RWA has drop {}

/// Held by the backend operator; gates every value-moving entry function.
public struct OperatorCap has key, store { id: UID }

/// One issued real-world asset. Shared; `token_ref` in the adapter is its id.
public struct Asset has key {
    id: UID,
    name: String,
    symbol: String,
    decimals: u8,
    asset_type: String,   // "bond" | "equity" | "fund" | ...
    jurisdiction: String,
    issuer: String,       // legal entity of record
    total_supply: u64,
    treasury: u64,        // operator-held (undistributed) balance
    holders: Table<address, u64>,
    audit: ID,            // this asset's AuditLog
    paused: bool,
}

public struct AssetIssued has copy, drop {
    asset: ID,
    audit: ID,
    symbol: String,
    supply: u64,
}

const ENotEnough: u64 = 1;
const EKyc: u64 = 2;
const EFrozen: u64 = 3;
const EPaused: u64 = 4;

/// Publish-time setup: create the closed-loop currency, wire the allowlist (KYC)
/// rule to the transfer action, share the policy, and hand all caps to the operator.
fun init(otw: RWA, ctx: &mut TxContext) {
    let (treasury_cap, metadata) = coin::create_currency(
        otw,
        6,
        b"RWA",
        b"Laminaa RWA",
        b"Closed-loop permissioned real-world-asset token family",
        option::none(),
        ctx,
    );
    transfer::public_freeze_object(metadata);

    let (mut policy, policy_cap) = token::new_policy(&treasury_cap, ctx);
    // Gate the closed-loop transfer action with the allowlist (KYC) rule, then
    // install its (empty) config. With a rule present and no `allow`, a transfer
    // only confirms when `allowlist::verify` has approved it.
    token::add_rule_for_action<RWA, Allowlist>(
        &mut policy, &policy_cap, token::transfer_action(), ctx,
    );
    allowlist::init_config<RWA>(&mut policy, &policy_cap, ctx);
    token::share_policy(policy);

    let op = ctx.sender();
    transfer::public_transfer(treasury_cap, op);
    transfer::public_transfer(policy_cap, op);
    transfer::transfer(OperatorCap { id: object::new(ctx) }, op);
}

// ─── issuance ────────────────────────────────────────────────────────────────

/// Issue an asset: opens its audit topic and creates the shared `Asset` ledger
/// with the full initial supply credited to the operator treasury. The created
/// `Asset` and `AuditLog` object ids are read from the tx effects by the adapter.
public fun issue_asset(
    _: &OperatorCap,
    name: String,
    symbol: String,
    decimals: u8,
    initial_supply: u64,
    asset_type: String,
    jurisdiction: String,
    issuer: String,
    ctx: &mut TxContext,
) {
    let audit_id = audit::open(symbol, ctx);
    let asset = Asset {
        id: object::new(ctx),
        name,
        symbol,
        decimals,
        asset_type,
        jurisdiction,
        issuer,
        total_supply: initial_supply,
        treasury: initial_supply,
        holders: table::new(ctx),
        audit: audit_id,
        paused: false,
    };
    event::emit(AssetIssued {
        asset: object::id(&asset), audit: audit_id, symbol: asset.symbol, supply: initial_supply,
    });
    transfer::share_object(asset);
}

// ─── supply ──────────────────────────────────────────────────────────────────

public fun mint(_: &OperatorCap, asset: &mut Asset, amount: u64) {
    asset.total_supply = asset.total_supply + amount;
    asset.treasury = asset.treasury + amount;
}

public fun burn(_: &OperatorCap, asset: &mut Asset, amount: u64) {
    assert!(asset.treasury >= amount, ENotEnough);
    asset.treasury = asset.treasury - amount;
    asset.total_supply = asset.total_supply - amount;
}

// ─── compliance (operates on the shared TokenPolicy allowlist) ────────────────

public fun grant_kyc(
    _: &OperatorCap, policy: &mut TokenPolicy<RWA>, cap: &TokenPolicyCap<RWA>, who: address,
) { allowlist::grant(policy, cap, who); }

public fun revoke_kyc(
    _: &OperatorCap, policy: &mut TokenPolicy<RWA>, cap: &TokenPolicyCap<RWA>, who: address,
) { allowlist::revoke(policy, cap, who); }

public fun freeze_holder(
    _: &OperatorCap, policy: &mut TokenPolicy<RWA>, cap: &TokenPolicyCap<RWA>, who: address,
) { allowlist::freeze_addr(policy, cap, who); }

public fun unfreeze_holder(
    _: &OperatorCap, policy: &mut TokenPolicy<RWA>, cap: &TokenPolicyCap<RWA>, who: address,
) { allowlist::unfreeze_addr(policy, cap, who); }

// ─── settlement (ledger) ──────────────────────────────────────────────────────

/// Credit `amount` to a holder. Compliance is enforced against the closed-loop
/// policy's allowlist — the same config `confirm_request` checks — so the ledger
/// can never diverge from the token's own KYC rules.
public fun transfer(
    _: &OperatorCap,
    policy: &TokenPolicy<RWA>,
    asset: &mut Asset,
    to: address,
    amount: u64,
) {
    assert!(!asset.paused, EPaused);
    assert!(allowlist::is_kyc(policy, to), EKyc);
    assert!(!allowlist::is_frozen(policy, to), EFrozen);
    assert!(asset.treasury >= amount, ENotEnough);
    asset.treasury = asset.treasury - amount;
    if (asset.holders.contains(to)) {
        let b = asset.holders.borrow_mut(to);
        *b = *b + amount;
    } else {
        asset.holders.add(to, amount);
    };
}

/// Maturity claw-back: pull tokens from a holder back to treasury (issuer
/// authority). The Sui mirror of LaminaRWAToken.forceRedeem.
public fun force_redeem(
    _: &OperatorCap, asset: &mut Asset, holder: address, amount: u64,
) {
    assert!(asset.holders.contains(holder), ENotEnough);
    let b = asset.holders.borrow_mut(holder);
    assert!(*b >= amount, ENotEnough);
    *b = *b - amount;
    asset.treasury = asset.treasury + amount;
}

public fun set_paused(_: &OperatorCap, asset: &mut Asset, paused: bool) {
    asset.paused = paused;
}

// ─── audit ─────────────────────────────────────────────────────────────────────

/// Append an audit entry to an asset's topic. Called by the services for every
/// state-changing action (issuance, mint, transfer, kyc, nav, coupon, redeem).
public fun write_audit(
    _: &OperatorCap, log: &mut AuditLog, agent: String, action: String, details: String,
) { audit::write(log, agent, action, details); }

// ─── closed-loop showcase ─────────────────────────────────────────────────────

/// Settle a *real* closed-loop `Token<RWA>` to a holder, enforced end-to-end by
/// the standard: mint → transfer → allowlist verify → confirm. Aborts (reverting
/// the whole tx) if `to` is not KYC'd. Canonical proof the compliance is
/// type-level, not bolted on.
public fun settle_closed_loop(
    _: &OperatorCap,
    treasury_cap: &mut TreasuryCap<RWA>,
    policy: &mut TokenPolicy<RWA>,
    to: address,
    amount: u64,
    ctx: &mut TxContext,
) {
    let tok = token::mint(treasury_cap, amount, ctx);
    let mut req = token::transfer(tok, to, ctx);
    allowlist::verify(policy, &mut req, ctx);
    let (_name, _amt, _sender, _recipient) = token::confirm_request_mut(policy, req, ctx);
}

// ─── views (read via devInspect) ──────────────────────────────────────────────

public fun balance_of(asset: &Asset, who: address): u64 {
    if (asset.holders.contains(who)) *asset.holders.borrow(who) else 0
}

public fun treasury_of(asset: &Asset): u64 { asset.treasury }
public fun total_supply_of(asset: &Asset): u64 { asset.total_supply }
public fun audit_of(asset: &Asset): ID { asset.audit }

#[test_only]
public fun init_for_testing(ctx: &mut TxContext) { init(RWA {}, ctx) }
