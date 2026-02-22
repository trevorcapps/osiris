import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities


class WHOIngestor(BaseIngestor):
    name = "WHO Disease Outbreaks"
    source = EventSource.WHO
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # WHO Disease Outbreak News API (OData)
            resp = await client.get(
                "https://www.who.int/api/hubs/diseaseoutbreaknews",
                params={"$top": 30, "$orderby": "PublicationDate desc"}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for item in data.get("value", []):
                title = item.get("Title", "") or item.get("Name", "")
                summary = item.get("Summary", "") or item.get("Description", "")
                pub_date = item.get("PublicationDate", "")
                url = item.get("CanonicalUrl", "") or item.get("ItemUrl", "")
                country = item.get("CountryName", "")

                try:
                    ts = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
                except (ValueError, TypeError, AttributeError):
                    ts = datetime.utcnow()

                entities_found = extract_entities(title)

                events.append(GeoEvent(
                    source=EventSource.WHO,
                    event_type=EventType.HEALTH,
                    title=title[:300],
                    description=summary[:500],
                    lat=None,
                    lon=None,
                    timestamp=ts,
                    entities=entities_found,
                    url=url,
                    severity="high",
                    metadata={
                        "source": "WHO DON",
                        "country": country,
                    }
                ))
        return events
