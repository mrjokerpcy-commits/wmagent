"""
Celery tasks — the scheduled jobs that run the pipeline.
"""

import asyncio
import json
import redis as redis_lib
from core.celery_app import app
from core.config import settings


def get_redis():
    return redis_lib.from_url(settings.redis_url)


@app.task(name="core.tasks.ingest_gdelt")
def ingest_gdelt():
    from collectors.gdelt import fetch_latest_gdelt_events
    r = get_redis()

    events = asyncio.run(fetch_latest_gdelt_events(limit=50))
    count = 0
    for event in events:
        r.rpush("events:raw", event.model_dump_json())
        count += 1

    print(f"[gdelt] ingested {count} events")
    return count


@app.task(name="core.tasks.ingest_polymarket")
def ingest_polymarket():
    from collectors.polymarket import fetch_moving_markets
    r = get_redis()

    events = asyncio.run(fetch_moving_markets(volume_threshold=5000))
    count = 0
    for event in events:
        r.rpush("events:raw", event.model_dump_json())
        count += 1

    print(f"[polymarket] ingested {count} markets")
    return count


@app.task(name="core.tasks.classify_events")
def classify_events():
    from agents.news_agent import classify_events as _classify
    from models.event import Event
    import asyncio

    r = get_redis()
    raw_items = r.lrange("events:raw", 0, 19)
    if not raw_items:
        return 0

    events = [Event.model_validate_json(item) for item in raw_items]
    classifications = asyncio.run(_classify(events))

    for c in classifications:
        if float(c.get("severity", 0)) > 0.7:
            r.publish("signals:hot", json.dumps(c))
        r.hset(
            f"event:classified:{c['id']}",
            mapping={
                k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
                for k, v in c.items()
            },
        )

    r.ltrim("events:raw", len(raw_items), -1)
    print(f"[news_agent] classified {len(classifications)} events")
    return len(classifications)


@app.task(name="core.tasks.snapshot_prices")
def snapshot_prices():
    from collectors.prices import fetch_all_prices
    r = get_redis()

    prices = asyncio.run(fetch_all_prices())
    r.set("prices:latest", json.dumps(prices))
    print(f"[prices] snapshot of {len(prices)} assets")
    return len(prices)
