"""
GDELT Collector
Updates every 15 minutes, free, global coverage.
Endpoint: http://data.gdeltproject.org/gdeltv2/lastupdate.txt
"""

import httpx
import csv
import io
import zipfile
from datetime import datetime, timezone
from models.event import Event, Category, GeoPoint


GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"


async def fetch_latest_gdelt_events(limit: int = 100) -> list[Event]:
    async with httpx.AsyncClient(timeout=30) as client:
        # Get the latest file URL
        resp = await client.get(GDELT_LAST_UPDATE_URL)
        resp.raise_for_status()

        # Parse the manifest — third line is the GKG (Global Knowledge Graph) CSV
        lines = resp.text.strip().split("\n")
        # First line is the main events CSV
        parts = lines[0].strip().split(" ")
        csv_url = parts[2]

        # Download the CSV zip
        zip_resp = await client.get(csv_url)
        zip_resp.raise_for_status()

    events = []
    with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as z:
        name = z.namelist()[0]
        with z.open(name) as f:
            reader = csv.reader(io.TextIOWrapper(f, encoding="latin-1"), delimiter="\t")
            for i, row in enumerate(reader):
                if i >= limit:
                    break
                try:
                    event = _parse_gdelt_row(row)
                    if event:
                        events.append(event)
                except Exception:
                    continue

    return events


def _parse_gdelt_row(row: list[str]) -> Event | None:
    # GDELT 2.0 events CSV has 61 columns
    if len(row) < 61:
        return None

    try:
        lat = float(row[56]) if row[56] else None
        lng = float(row[57]) if row[57] else None
        geo = GeoPoint(lat=lat, lng=lng) if lat and lng else None

        country_code = row[51] if row[51] else ""
        avg_tone = float(row[34]) if row[34] else 0.0
        # Tone is -100 to +100; normalize severity as distance from 0
        severity = min(abs(avg_tone) / 20, 1.0)

        timestamp_str = row[1]  # YYYYMMDDHHMMSS
        timestamp = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S").replace(
            tzinfo=timezone.utc
        )

        return Event(
            timestamp=timestamp,
            source="gdelt",
            source_url=row[60] if row[60] else "",
            headline=row[60] if row[60] else "",
            body="",
            category=_gdelt_category(row[26]),
            subcategory=row[26] if row[26] else "",
            geo=geo,
            countries=[country_code] if country_code else [],
            severity=severity,
            confidence=0.6,  # GDELT baseline confidence
            raw={"row_index": row[0]},
        )
    except (ValueError, IndexError):
        return None


def _gdelt_category(event_code: str) -> Category:
    if not event_code:
        return Category.POLITICAL
    code = event_code[:2]
    mapping = {
        "18": Category.CONFLICT,  # Assault
        "19": Category.CONFLICT,  # Fight
        "20": Category.CONFLICT,  # Engage in unconventional mass violence
        "14": Category.POLITICAL,  # Protest
        "15": Category.POLITICAL,  # Exhibit force posture
        "03": Category.ECONOMIC,   # Express intent to meet or negotiate
    }
    return mapping.get(code, Category.POLITICAL)
