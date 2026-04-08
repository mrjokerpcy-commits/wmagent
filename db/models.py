"""
SQLAlchemy ORM models — maps to PostgreSQL tables.
These are separate from the Pydantic models in /models/.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    String, Float, DateTime, Text, JSON, ForeignKey, Index, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from core.database import Base
import enum


class CategoryEnum(str, enum.Enum):
    CONFLICT = "CONFLICT"
    ECONOMIC = "ECONOMIC"
    POLITICAL = "POLITICAL"
    CLIMATE = "CLIMATE"
    CYBER = "CYBER"
    SOCIAL = "SOCIAL"


class UrgencyEnum(str, enum.Enum):
    ROUTINE = "routine"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class DirectionEnum(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class TradeStatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


def _now():
    return datetime.now(timezone.utc)


class EventDB(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    source_url: Mapped[str] = mapped_column(Text, default="")
    headline: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[CategoryEnum] = mapped_column(SAEnum(CategoryEnum), index=True)
    subcategory: Mapped[str] = mapped_column(String(128), default="")
    geo_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    geo_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    countries: Mapped[list] = mapped_column(JSON, default=list)
    entities: Mapped[list] = mapped_column(JSON, default=list)
    severity: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    velocity: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    urgency: Mapped[UrgencyEnum | None] = mapped_column(SAEnum(UrgencyEnum), nullable=True)
    affected_assets: Mapped[list] = mapped_column(JSON, default=list)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    signals: Mapped[list["SignalDB"]] = relationship(back_populates="event")

    __table_args__ = (
        Index("ix_events_severity_timestamp", "severity", "timestamp"),
        Index("ix_events_category_timestamp", "category", "timestamp"),
    )


class SignalDB(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    asset: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[DirectionEnum] = mapped_column(SAEnum(DirectionEnum))
    magnitude: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, index=True)
    timeframe: Mapped[str] = mapped_column(String(8))
    reasoning: Mapped[str] = mapped_column(Text)
    correlated_assets: Mapped[list] = mapped_column(JSON, default=list)
    historical_precedent: Mapped[str] = mapped_column(Text, default="")
    second_order: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Outcome tracking (filled in after timeframe expires)
    actual_move_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    was_correct: Mapped[bool | None] = mapped_column(nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    event: Mapped["EventDB"] = relationship(back_populates="signals")
    trades: Mapped[list["TradeDB"]] = relationship(back_populates="signal")

    __table_args__ = (
        Index("ix_signals_asset_confidence", "asset", "confidence"),
    )


class TradeDB(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    signal_id: Mapped[str] = mapped_column(ForeignKey("signals.id"), index=True)
    asset: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[DirectionEnum] = mapped_column(SAEnum(DirectionEnum))
    size_pct: Mapped[float] = mapped_column(Float)
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    take_profit: Mapped[float] = mapped_column(Float)
    status: Mapped[TradeStatusEnum] = mapped_column(
        SAEnum(TradeStatusEnum), default=TradeStatusEnum.PENDING, index=True
    )
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    close_reason: Mapped[str] = mapped_column(String(64), default="")

    # Alpaca order tracking
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    signal: Mapped["SignalDB"] = relationship(back_populates="trades")
