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
            resp = await client.get(
                "https://www.who.int/feeds/entity/don/en/rss.xml"
            )
            if resp.status_code != 200:
                return events

            import feedparser
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:30]:
                title = entry.get("title", "")
                desc = entry.get("summary", "")
                link = entry.get("link", "")

                try:
                    if entry.get("published_parsed"):
                        ts = datetime(*entry.published_parsed[:6])
                    else:
                        ts = datetime.utcnow()
                except Exception:
                    ts = datetime.utcnow()

                entities_found = extract_entities(title)

                events.append(GeoEvent(
                    source=EventSource.WHO,
                    event_type=EventType.HEALTH,
                    title=title,
                    description=desc[:500],
                    lat=None,
                    lon=None,
                    timestamp=ts,
                    entities=entities_found,
                    url=link,
                    severity="high",
                    metadata={"source": "WHO DON"}
                ))
        return events
