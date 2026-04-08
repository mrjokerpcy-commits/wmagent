from celery import Celery
from celery.schedules import crontab
from core.config import settings

app = Celery("macro", broker=settings.redis_url, backend=settings.redis_url)

app.conf.timezone = "UTC"

app.conf.beat_schedule = {
    # GDELT updates every 15 minutes
    "ingest-gdelt": {
        "task": "core.tasks.ingest_gdelt",
        "schedule": 900,  # 15 minutes
    },
    # Polymarket — check for moving markets every 10 minutes
    "ingest-polymarket": {
        "task": "core.tasks.ingest_polymarket",
        "schedule": 600,
    },
    # News agent classification — every 60 seconds
    "classify-events": {
        "task": "core.tasks.classify_events",
        "schedule": 60,
    },
    # Price snapshot — every 5 minutes
    "snapshot-prices": {
        "task": "core.tasks.snapshot_prices",
        "schedule": 300,
    },
}
