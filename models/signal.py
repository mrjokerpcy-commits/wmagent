from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional
import uuid


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class TradeStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class Signal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    asset: str                      # "BTC", "CL=F", "GLD", "AAPL"
    direction: Direction
    magnitude: float                # expected % move
    confidence: float               # 0.0 → 1.0
    timeframe: str                  # "1h" | "24h" | "7d"
    reasoning: str
    correlated_assets: list[str] = []
    historical_precedent: str = ""
    second_order: list["Signal"] = []


class Trade(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    signal_id: str
    asset: str
    direction: Direction
    size: float                     # % of portfolio
    entry_price: float
    stop_loss: float
    take_profit: float
    status: TradeStatus = TradeStatus.PENDING
    pnl: float = 0.0
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    close_reason: str = ""          # "take_profit" | "stop_loss" | "signal_reversal"
