"""
Database CRUD operations.
"""

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import EventDB, SignalDB, TradeDB, TradeStatusEnum
from models.event import Event
from models.signal import Signal, Trade
import uuid


# ── Events ──────────────────────────────────────────────────────────────────

async def save_event(db: AsyncSession, event: Event) -> EventDB:
    db_event = EventDB(
        id=event.id,
        timestamp=event.timestamp,
        source=event.source,
        source_url=event.source_url,
        headline=event.headline,
        body=event.body,
        category=event.category.value,
        subcategory=event.subcategory,
        geo_lat=event.geo.lat if event.geo else None,
        geo_lng=event.geo.lng if event.geo else None,
        countries=event.countries,
        entities=event.entities,
        severity=event.severity,
        velocity=event.velocity,
        confidence=event.confidence,
        raw=event.raw,
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event


async def get_latest_events(
    db: AsyncSession,
    limit: int = 50,
    min_severity: float = 0.0,
    category: str | None = None,
) -> list[EventDB]:
    q = select(EventDB).where(EventDB.severity >= min_severity)
    if category:
        q = q.where(EventDB.category == category)
    q = q.order_by(desc(EventDB.timestamp)).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


async def get_hot_events(db: AsyncSession, hours: int = 1) -> list[EventDB]:
    """Events with severity > 0.7 in the last N hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = (
        select(EventDB)
        .where(and_(EventDB.severity >= 0.7, EventDB.timestamp >= cutoff))
        .order_by(desc(EventDB.severity))
    )
    result = await db.execute(q)
    return result.scalars().all()


# ── Signals ──────────────────────────────────────────────────────────────────

async def save_signal(db: AsyncSession, signal: Signal) -> SignalDB:
    db_signal = SignalDB(
        id=signal.id,
        event_id=signal.event_id,
        asset=signal.asset,
        direction=signal.direction.value,
        magnitude=signal.magnitude,
        confidence=signal.confidence,
        timeframe=signal.timeframe,
        reasoning=signal.reasoning,
        correlated_assets=signal.correlated_assets,
        historical_precedent=signal.historical_precedent,
        second_order=[s.model_dump() for s in signal.second_order],
    )
    db.add(db_signal)
    await db.commit()
    await db.refresh(db_signal)
    return db_signal


async def get_active_signals(
    db: AsyncSession,
    min_confidence: float = 0.0,
) -> list[SignalDB]:
    q = (
        select(SignalDB)
        .where(and_(SignalDB.confidence >= min_confidence, SignalDB.was_correct.is_(None)))
        .order_by(desc(SignalDB.confidence))
    )
    result = await db.execute(q)
    return result.scalars().all()


async def resolve_signal(
    db: AsyncSession,
    signal_id: str,
    actual_move_pct: float,
    was_correct: bool,
) -> SignalDB | None:
    result = await db.execute(select(SignalDB).where(SignalDB.id == signal_id))
    signal = result.scalar_one_or_none()
    if signal:
        signal.actual_move_pct = actual_move_pct
        signal.was_correct = was_correct
        signal.resolved_at = datetime.now(timezone.utc)
        await db.commit()
    return signal


# ── Trades ───────────────────────────────────────────────────────────────────

async def save_trade(db: AsyncSession, trade: Trade) -> TradeDB:
    db_trade = TradeDB(
        id=trade.id,
        signal_id=trade.signal_id,
        asset=trade.asset,
        direction=trade.direction.value,
        size_pct=trade.size,
        entry_price=trade.entry_price,
        stop_loss=trade.stop_loss,
        take_profit=trade.take_profit,
    )
    db.add(db_trade)
    await db.commit()
    await db.refresh(db_trade)
    return db_trade


async def get_open_trades(db: AsyncSession) -> list[TradeDB]:
    q = select(TradeDB).where(TradeDB.status == TradeStatusEnum.OPEN)
    result = await db.execute(q)
    return result.scalars().all()


async def close_trade(
    db: AsyncSession,
    trade_id: str,
    pnl: float,
    close_reason: str,
) -> TradeDB | None:
    result = await db.execute(select(TradeDB).where(TradeDB.id == trade_id))
    trade = result.scalar_one_or_none()
    if trade:
        trade.status = TradeStatusEnum.CLOSED
        trade.pnl = pnl
        trade.close_reason = close_reason
        trade.closed_at = datetime.now(timezone.utc)
        await db.commit()
    return trade


# ── Stats ────────────────────────────────────────────────────────────────────

async def get_performance_stats(db: AsyncSession) -> dict:
    """Win rate, total PnL, trade count."""
    result = await db.execute(
        select(TradeDB).where(TradeDB.status == TradeStatusEnum.CLOSED)
    )
    closed = result.scalars().all()

    if not closed:
        return {"total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}

    wins = sum(1 for t in closed if t.pnl > 0)
    return {
        "total_trades": len(closed),
        "win_rate": round(wins / len(closed), 4),
        "total_pnl": round(sum(t.pnl for t in closed), 4),
        "avg_pnl": round(sum(t.pnl for t in closed) / len(closed), 4),
    }
