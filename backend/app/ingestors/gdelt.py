import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities


class GDELTIngestor(BaseIngestor):
    name = "GDELT"
    source = EventSource.GDELT
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        # GDELT GKG (Global Knowledge Graph) — last 15 min
        async with httpx.AsyncClient(timeout=30) as client:
            # Use GDELT DOC API for recent events
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": "",
                    "mode": "artlist",
                    "maxrecords": 75,
                    "format": "json",
                    "sort": "datedesc",
                    "timespan": "60min"
                }
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for article in data.get("articles", []):
                lat = None
                lon = None
                # Try to extract coordinates from socialimage or use tone location
                if article.get("sourcecountry"):
                    pass  # We'll geocode by country in a future iteration

                title = article.get("title", "")
                desc = article.get("seendate", "")
                url = article.get("url", "")
                domain = article.get("domain", "")
                language = article.get("language", "")

                try:
                    ts = datetime.strptime(
                        article.get("seendate", "")[:14], "%Y%m%dT%H%M%S"
                    )
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                entities_found = extract_entities(title)

                event = GeoEvent(
                    source=EventSource.GDELT,
                    event_type=EventType.NEWS,
                    title=title,
                    description=f"Source: {domain} | Language: {language}",
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    entities=entities_found,
                    url=url,
                    metadata={
                        "domain": domain,
                        "language": language,
                        "country": article.get("sourcecountry", ""),
                    }
                )
                events.append(event)
        return events
