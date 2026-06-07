/// On-chain audit trail — the Sui analogue of AuditLog.sol.
///
/// One `AuditLog` shared object per asset (one "topic"). Every state-changing
/// action emits an `AuditRecord` event tagged with the log id and a monotonic
/// sequence number, so the full history is queryable off-chain by event type +
/// log id (see SuiAdapter.read_audit). Keeping the running `seq` on the object
/// gives stable, gap-free ordering. Like the EVM AuditLog, this only *opens* a
/// topic — entries are written explicitly by the services via `rwa::write_audit`,
/// so the audit trail is never duplicated by self-logging value functions.
module lamina_rwa::audit;

use std::string::String;
use sui::event;

public struct AuditLog has key {
    id: UID,
    topic: String,
    seq: u64,
}

/// Emitted on every audit write. Indexed off-chain by `log` to reconstruct an
/// asset's history in order.
public struct AuditRecord has copy, drop {
    log: ID,
    seq: u64,
    agent: String,
    action: String,
    details: String,
}

/// Create an audit topic and share it. Returns the new log's id so issuance can
/// store it on the `Asset`.
public(package) fun open(topic: String, ctx: &mut TxContext): ID {
    let log = AuditLog { id: object::new(ctx), topic, seq: 0 };
    let id = object::id(&log);
    transfer::share_object(log);
    id
}

/// Append one record to an existing topic. Returns the assigned sequence number.
public(package) fun write(
    log: &mut AuditLog,
    agent: String,
    action: String,
    details: String,
): u64 {
    let seq = log.seq;
    event::emit(AuditRecord { log: object::id(log), seq, agent, action, details });
    log.seq = seq + 1;
    seq
}

public fun seq(log: &AuditLog): u64 { log.seq }
