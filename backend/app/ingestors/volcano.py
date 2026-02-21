import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class VolcanoIngestor(BaseIngestor):
    name = "Smithsonian Volcanoes"
    source = EventSource.VOLCANO
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # Smithsonian GVP weekly reports RSS
            resp = await client.get(
                "https://volcano.si.edu/news/WeeklyVolcanoRSS.xml"
            )
            if resp.status_code != 200:
                return events
            import feedparser
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:20]:
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

                events.append(GeoEvent(
                    source=EventSource.VOLCANO,
                    event_type=EventType.VOLCANO,
                    title=title,
                    description=desc[:500],
                    lat=None,
                    lon=None,
                    timestamp=ts,
                    url=link,
                    severity="high",
                    metadata={"source": "Smithsonian GVP"}
                ))
        return events
