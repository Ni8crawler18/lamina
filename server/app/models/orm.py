"""SQLAlchemy ORM models (Postgres).

Ported from the old `server/database.py` schema with two multi-chain changes:
  * `assets.chain` — the chain slug an asset lives on (authoritative; everything
    else joins through `asset_id`).
  * HCS-specific audit columns renamed to chain-neutral `onchain_*`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    chain: Mapped[str] = mapped_column(String(64), index=True)  # chain slug
    name: Mapped[str] = mapped_column(String(255))
    symbol: Mapped[str] = mapped_column(String(32))
    token_id: Mapped[str | None] = mapped_column(String(128), nullable=True)   # token_ref
    topic_id: Mapped[str | None] = mapped_column(String(128), nullable=True)   # audit topic_ref
    asset_type: Mapped[str] = mapped_column(String(32), default="bond")
    total_supply: Mapped[int] = mapped_column(BigInteger)
    decimals: Mapped[int] = mapped_column(Integer, default=2)
    coupon_rate: Mapped[float] = mapped_column(Float, default=0.0)
    maturity_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    nav: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    jurisdiction: Mapped[str] = mapped_column(String(8), default="US")
    investor_type: Mapped[str] = mapped_column(String(32), default="accredited")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    holders: Mapped[list["Holder"]] = relationship(back_populates="asset")


class Holder(Base):
    __tablename__ = "holders"
    __table_args__ = (UniqueConstraint("account_id", "asset_id", name="uq_holder_account_asset"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(128), index=True)  # holder_ref
    private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    balance: Mapped[int] = mapped_column(BigInteger, default=0)
    kyc_status: Mapped[str] = mapped_column(String(32), default="pending")
    jurisdiction: Mapped[str | None] = mapped_column(String(8), default="US")
    investor_type: Mapped[str | None] = mapped_column(String(32), default="accredited")
    whitelisted: Mapped[bool] = mapped_column(Boolean, default=False)
    token_associated: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    ofac_status: Mapped[str] = mapped_column(String(32), default="pending")
    ofac_screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    asset: Mapped["Asset"] = relationship(back_populates="holders")


class ScheduledEvent(Base):
    __tablename__ = "scheduled_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32))   # coupon_payment | maturity | nav_update
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLogEntry(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(64))
    agent: Mapped[str] = mapped_column(String(32))
    details: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    onchain_sequence: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    onchain_timestamp: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id"), index=True)
    report_type: Mapped[str] = mapped_column(String(32))
    period: Mapped[str] = mapped_column(String(32))
    file_path: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_account_id: Mapped[str] = mapped_column(String(128), index=True)
    holder_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    asset_id: Mapped[int | None] = mapped_column(ForeignKey("assets.id"), nullable=True, index=True)
    is_match: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    match_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    matched_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    matched_program: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action_taken: Mapped[str | None] = mapped_column(String(64), nullable=True)
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
