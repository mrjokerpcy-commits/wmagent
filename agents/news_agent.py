"""
NEWS_AGENT — Haiku
Runs every 60s. Classifies raw events, scores severity, flags urgency.
"""

import json
import anthropic
from models.event import Event, Category

client = anthropic.Anthropic()

SYSTEM_PROMPT = """You are a geopolitical intelligence analyst.
You receive raw news events and classify them precisely.
Always return valid JSON. Be terse and accurate."""

CLASSIFICATION_PROMPT = """Classify these {count} events:

{events}

For each event return a JSON array with objects:
{{
  "id": "<event id>",
  "is_duplicate": false,
  "category": "CONFLICT|ECONOMIC|POLITICAL|CLIMATE|CYBER|SOCIAL",
  "subcategory": "<specific subcategory>",
  "severity": 0.0,
  "urgency": "routine|elevated|critical",
  "countries": ["ISO2"],
  "affected_assets": ["BTC", "CL=F", "SPY"],
  "summary": "<one sentence>"
}}

Severity guide:
  0.0–0.3: routine/background noise
  0.3–0.6: elevated, worth watching
  0.6–0.8: significant market impact likely
  0.8–1.0: critical, immediate reaction expected

Return ONLY the JSON array, no commentary."""


async def classify_events(events: list[Event]) -> list[dict]:
    """
    Classify a batch of raw events.
    Returns enriched classification objects.
    """
    if not events:
        return []

    events_text = "\n\n".join(
        f"[{i+1}] ID: {e.id}\nHeadline: {e.headline}\nSource: {e.source}\nCountries: {e.countries}"
        for i, e in enumerate(events)
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(
                    count=len(events), events=events_text
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return json.loads(raw)


async def run(redis_client, db_session) -> None:
    """
    Main loop body — called by Celery task every 60s.
    Reads latest events from Redis, classifies, saves to DB.
    """
    # Pull latest 20 unclassified events from Redis queue
    raw_items = redis_client.lrange("events:raw", 0, 19)
    if not raw_items:
        return

    events = [Event.model_validate_json(item) for item in raw_items]
    classifications = await classify_events(events)

    # Save classifications back
    for classification in classifications:
        if classification.get("severity", 0) > 0.7:
            # Hot signal — push to priority channel
            redis_client.publish("signals:hot", json.dumps(classification))

        redis_client.hset(
            f"event:classified:{classification['id']}",
            mapping={k: json.dumps(v) if isinstance(v, (list, dict)) else str(v)
                     for k, v in classification.items()}
        )

    # Remove processed items from queue
    redis_client.ltrim("events:raw", len(raw_items), -1)
