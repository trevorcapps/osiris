import httpx
from datetime import datetime, timedelta
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities
from app.config import settings


class ACLEDIngestor(BaseIngestor):
    name = "ACLED Conflict Data"
    source = EventSource.ACLED
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.acled_api_key and settings.acled_email)

    async def fetch(self) -> List[GeoEvent]:
        events = []
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.acleddata.com/acled/read",
                params={
                    "key": settings.acled_api_key,
                    "email": settings.acled_email,
                    "event_date": f"{week_ago}|",
                    "event_date_where": ">=",
                    "limit": 100,
                }
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for item in data.get("data", []):
                lat = float(item.get("latitude", 0)) if item.get("latitude") else None
                lon = float(item.get("longitude", 0)) if item.get("longitude") else None
                try:
                    ts = datetime.strptime(item.get("event_date", ""), "%Y-%m-%d")
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                title = f"{item.get('event_type', 'Event')}: {item.get('country', '')}"
                notes = item.get("notes", "")
                entities_found = extract_entities(notes)

                fatalities = int(item.get("fatalities", 0) or 0)
                severity = "critical" if fatalities >= 10 else "high" if fatalities >= 1 else "medium"

                events.append(GeoEvent(
                    source=EventSource.ACLED,
                    event_type=EventType.CONFLICT,
                    title=title,
                    description=notes[:500],
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    entities=entities_found,
                    severity=severity,
                    metadata={
                        "event_type": item.get("event_type"),
                        "sub_event_type": item.get("sub_event_type"),
                        "actor1": item.get("actor1"),
                        "actor2": item.get("actor2"),
                        "fatalities": fatalities,
                        "country": item.get("country"),
                        "region": item.get("region"),
                        "source": item.get("source"),
                    }
                ))
        return events
