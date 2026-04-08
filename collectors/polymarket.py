"""
Polymarket Collector
Prediction market odds on geopolitical events.
Key signal: odds moving BEFORE news breaks.
API: https://gamma-api.polymarket.com
"""

import httpx
from datetime import datetime, timezone
from models.event import Event, Category


POLYMARKET_API = "https://gamma-api.polymarket.com"


async def fetch_active_markets(limit: int = 50) -> list[dict]:
    """Fetch active markets sorted by volume."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{POLYMARKET_API}/markets",
            params={"active": "true", "limit": limit, "order": "volume24hr", "ascending": "false"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_moving_markets(volume_threshold: float = 10000) -> list[Event]:
    """
    Returns markets with significant volume movement — these often precede news.
    A sharp odds move = smart money knows something.
    """
    markets = await fetch_active_markets(limit=100)
    events = []

    for market in markets:
        volume_24h = float(market.get("volume24hr", 0) or 0)
        if volume_24h < volume_threshold:
            continue

        event = _market_to_event(market)
        if event:
            events.append(event)

    return events


def _market_to_event(market: dict) -> Event | None:
    try:
        question = market.get("question", "")
        if not question:
            return None

        # Infer category from question text
        category = _infer_category(question)

        # Use volume as a proxy for severity/confidence
        volume = float(market.get("volume", 0) or 0)
        severity = min(volume / 1_000_000, 1.0)  # normalize to 0-1

        return Event(
            timestamp=datetime.now(timezone.utc),
            source="polymarket",
            source_url=f"https://polymarket.com/event/{market.get('slug', '')}",
            headline=question,
            body=market.get("description", ""),
            category=category,
            subcategory="prediction_market",
            countries=[],
            severity=severity,
            confidence=0.7,  # Polymarket is high-quality signal
            raw=market,
        )
    except Exception:
        return None


def _infer_category(question: str) -> Category:
    q = question.lower()
    if any(w in q for w in ["war", "attack", "military", "troops", "missile", "conflict"]):
        return Category.CONFLICT
    if any(w in q for w in ["fed", "rate", "gdp", "inflation", "recession", "earnings"]):
        return Category.ECONOMIC
    if any(w in q for w in ["election", "president", "congress", "vote", "sanction"]):
        return Category.POLITICAL
    if any(w in q for w in ["climate", "hurricane", "earthquake", "flood"]):
        return Category.CLIMATE
    if any(w in q for w in ["hack", "cyber", "breach", "ransomware"]):
        return Category.CYBER
    return Category.POLITICAL
