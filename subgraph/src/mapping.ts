import { AssetDeployed as AssetDeployedEvent } from "../generated/LaminaFactory/LaminaFactory";
import { ActionLogged as ActionLoggedEvent } from "../generated/AuditLog/AuditLog";
import {
  KYCGranted as KYCGrantedEvent,
  KYCRevoked as KYCRevokedEvent,
  AccountFrozen as AccountFrozenEvent,
  AccountUnfrozen as AccountUnfrozenEvent,
  Transfer as TransferEvent,
} from "../generated/templates/LaminaRWAToken/LaminaRWAToken";
import { LaminaRWAToken as LaminaRWATokenTemplate } from "../generated/templates";
import { Asset, AuditEntry, KycEvent, FreezeEvent, Transfer, TopicIndex } from "../generated/schema";

export function handleAssetDeployed(event: AssetDeployedEvent): void {
  const assetId = event.params.tokenAddress.toHexString();
  const asset = new Asset(assetId);
  asset.topicId = event.params.topicId;
  asset.name = event.params.name;
  asset.symbol = event.params.symbol;
  asset.deployer = event.params.deployer;
  asset.deployedAt = event.block.timestamp;
  asset.deployedAtTx = event.transaction.hash;
  asset.save();

  const topicIndex = new TopicIndex(event.params.topicId.toHexString());
  topicIndex.asset = assetId;
  topicIndex.save();

  // Start indexing this asset's own LaminaRWAToken contract (deployed
  // per-asset by the factory, so it can't be a static dataSource).
  LaminaRWATokenTemplate.create(event.params.tokenAddress);
}

export function handleActionLogged(event: ActionLoggedEvent): void {
  const id =
    event.params.topicId.toHexString() + "-" + event.params.sequenceNumber.toString();
  const entry = new AuditEntry(id);
  const topicIndex = TopicIndex.load(event.params.topicId.toHexString());
  entry.asset = topicIndex ? topicIndex.asset : null;
  entry.topicId = event.params.topicId;
  entry.sequenceNumber = event.params.sequenceNumber;
  entry.agent = event.params.agent;
  entry.action = event.params.action;
  entry.timestamp = event.params.timestamp;
  entry.txHash = event.transaction.hash;
  entry.save();
}

export function handleKYCGranted(event: KYCGrantedEvent): void {
  const id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  const e = new KycEvent(id);
  e.asset = event.address.toHexString();
  e.account = event.params.account;
  e.granted = true;
  e.timestamp = event.block.timestamp;
  e.txHash = event.transaction.hash;
  e.save();
}

export function handleKYCRevoked(event: KYCRevokedEvent): void {
  const id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  const e = new KycEvent(id);
  e.asset = event.address.toHexString();
  e.account = event.params.account;
  e.granted = false;
  e.timestamp = event.block.timestamp;
  e.txHash = event.transaction.hash;
  e.save();
}

export function handleAccountFrozen(event: AccountFrozenEvent): void {
  const id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  const e = new FreezeEvent(id);
  e.asset = event.address.toHexString();
  e.account = event.params.account;
  e.frozen = true;
  e.timestamp = event.block.timestamp;
  e.txHash = event.transaction.hash;
  e.save();
}

export function handleAccountUnfrozen(event: AccountUnfrozenEvent): void {
  const id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  const e = new FreezeEvent(id);
  e.asset = event.address.toHexString();
  e.account = event.params.account;
  e.frozen = false;
  e.timestamp = event.block.timestamp;
  e.txHash = event.transaction.hash;
  e.save();
}

export function handleTransfer(event: TransferEvent): void {
  const id = event.transaction.hash.toHexString() + "-" + event.logIndex.toString();
  const t = new Transfer(id);
  t.asset = event.address.toHexString();
  t.from = event.params.from;
  t.to = event.params.to;
  t.amount = event.params.value;
  t.timestamp = event.block.timestamp;
  t.txHash = event.transaction.hash;
  t.save();
}
