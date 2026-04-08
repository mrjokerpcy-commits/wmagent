from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class Category(str, Enum):
    CONFLICT = "CONFLICT"
    ECONOMIC = "ECONOMIC"
    POLITICAL = "POLITICAL"
    CLIMATE = "CLIMATE"
    CYBER = "CYBER"
    SOCIAL = "SOCIAL"


class GeoPoint(BaseModel):
    lat: float
    lng: float


class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime
    source: str  # "gdelt" | "telegram" | "acled" | ...
    source_url: str
    headline: str
    body: str
    category: Category
    subcategory: str
    geo: Optional[GeoPoint] = None
    countries: list[str] = []   # ISO codes
    entities: list[str] = []    # people, orgs, places extracted
    severity: float = 0.0       # 0.0 → 1.0
    velocity: float = 0.0       # how fast is this topic growing?
    confidence: float = 0.0     # how reliable is this source?
    raw: dict = {}              # original payload
