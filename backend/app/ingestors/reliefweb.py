import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities


class ReliefWebIngestor(BaseIngestor):
    name = "ReliefWeb"
    source = EventSource.RELIEFWEB
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.reliefweb.int/v1/disasters",
                params={
                    "appname": "osiris",
                    "limit": 50,
                    "fields[include][]": ["name", "description", "country", "date", "url", "glide", "primary_type", "status"],
                    "sort[]": "date:desc",
                    "filter[field]": "status",
                    "filter[value]": "current",
                }
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for item in data.get("data", []):
                fields = item.get("fields", {})
                title = fields.get("name", "Unknown Disaster")
                desc = fields.get("description", "")
                countries = fields.get("country", [])
                lat, lon = None, None
                country_name = ""
                if countries:
                    c = countries[0]
                    country_name = c.get("name", "")
                    loc = c.get("location", {})
                    if loc:
                        lat = loc.get("lat")
                        lon = loc.get("lon")

                try:
                    date_info = fields.get("date", {})
                    ts = datetime.fromisoformat(date_info.get("created", "").replace("Z", "+00:00"))
                except (ValueError, TypeError, AttributeError):
                    ts = datetime.utcnow()

                entities_found = extract_entities(title + " " + desc[:200])

                events.append(GeoEvent(
                    source=EventSource.RELIEFWEB,
                    event_type=EventType.HUMANITARIAN,
                    title=title,
                    description=desc[:500],
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    entities=entities_found,
                    url=fields.get("url"),
                    severity="high",
                    metadata={
                        "country": country_name,
                        "glide": fields.get("glide"),
                        "primary_type": fields.get("primary_type", {}).get("name") if isinstance(fields.get("primary_type"), dict) else None,
                    }
                ))
        return events
