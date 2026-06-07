/// KYC / sanctions gate for the closed-loop RWA token — the compliance layer the
/// fund manager chose: a `sui::token` TokenPolicy rule, not an ad-hoc mapping.
///
/// The rule's config (a KYC allowlist + a frozen/sanctions denylist) lives INSIDE
/// the `TokenPolicy<T>`. It is registered against the `transfer` action, so the
/// closed-loop standard itself refuses to settle a `Token<T>` to a non-KYC'd or
/// frozen address: `verify` aborts inside `confirm_request`. The same config is
/// read by the per-asset ledger (`rwa::transfer`) so there is one — and only one —
/// source of compliance truth on chain.
module lamina_rwa::allowlist;

use sui::token::{Self, TokenPolicy, TokenPolicyCap, ActionRequest};
use sui::vec_set::{Self, VecSet};

/// Rule witness. Registered for the transfer action of the RWA TokenPolicy.
public struct Allowlist has drop {}

/// Compliance state held inside the TokenPolicy as this rule's config.
public struct Config has store {
    kyc: VecSet<address>,    // addresses cleared to hold/receive (KYC granted)
    frozen: VecSet<address>, // addresses blocked (sanctions hit / frozen)
}

const EKycRequired: u64 = 1;
const EFrozen: u64 = 2;

/// Install an empty compliance config on a fresh policy (idempotent).
public(package) fun init_config<T>(
    policy: &mut TokenPolicy<T>,
    cap: &TokenPolicyCap<T>,
    ctx: &mut TxContext,
) {
    if (!token::has_rule_config<T, Allowlist>(policy)) {
        token::add_rule_config(
            Allowlist {},
            policy,
            cap,
            Config { kyc: vec_set::empty(), frozen: vec_set::empty() },
            ctx,
        );
    }
}

public(package) fun grant<T>(policy: &mut TokenPolicy<T>, cap: &TokenPolicyCap<T>, who: address) {
    let cfg = token::rule_config_mut<T, Allowlist, Config>(Allowlist {}, policy, cap);
    if (!cfg.kyc.contains(&who)) { cfg.kyc.insert(who); };
}

public(package) fun revoke<T>(policy: &mut TokenPolicy<T>, cap: &TokenPolicyCap<T>, who: address) {
    let cfg = token::rule_config_mut<T, Allowlist, Config>(Allowlist {}, policy, cap);
    if (cfg.kyc.contains(&who)) { cfg.kyc.remove(&who); };
}

public(package) fun freeze_addr<T>(policy: &mut TokenPolicy<T>, cap: &TokenPolicyCap<T>, who: address) {
    let cfg = token::rule_config_mut<T, Allowlist, Config>(Allowlist {}, policy, cap);
    if (!cfg.frozen.contains(&who)) { cfg.frozen.insert(who); };
}

public(package) fun unfreeze_addr<T>(policy: &mut TokenPolicy<T>, cap: &TokenPolicyCap<T>, who: address) {
    let cfg = token::rule_config_mut<T, Allowlist, Config>(Allowlist {}, policy, cap);
    if (cfg.frozen.contains(&who)) { cfg.frozen.remove(&who); };
}

public fun is_kyc<T>(policy: &TokenPolicy<T>, who: address): bool {
    if (!token::has_rule_config<T, Allowlist>(policy)) { return false };
    let cfg = token::rule_config<T, Allowlist, Config>(Allowlist {}, policy);
    cfg.kyc.contains(&who)
}

public fun is_frozen<T>(policy: &TokenPolicy<T>, who: address): bool {
    if (!token::has_rule_config<T, Allowlist>(policy)) { return false };
    let cfg = token::rule_config<T, Allowlist, Config>(Allowlist {}, policy);
    cfg.frozen.contains(&who)
}

/// Closed-loop hook: approve a `transfer` request iff the recipient is KYC'd and
/// not frozen. Called before `token::confirm_request`; an assert here reverts the
/// whole settlement, so a non-compliant transfer can never land.
public fun verify<T>(
    policy: &TokenPolicy<T>,
    request: &mut ActionRequest<T>,
    ctx: &mut TxContext,
) {
    let cfg = token::rule_config<T, Allowlist, Config>(Allowlist {}, policy);
    let recipient = token::recipient(request);
    if (recipient.is_some()) {
        let r = *recipient.borrow();
        assert!(cfg.kyc.contains(&r), EKycRequired);
        assert!(!cfg.frozen.contains(&r), EFrozen);
    };
    token::add_approval(Allowlist {}, request, ctx);
}
