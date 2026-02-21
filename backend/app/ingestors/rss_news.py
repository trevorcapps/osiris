import feedparser
from datetime import datetime
from typing import List
from email.utils import parsedate_to_datetime
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities

RSS_FEEDS = [
    ("Reuters World", "https://feeds.reuters.com/reuters/worldNews"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("AP Top News", "https://rsshub.app/apnews/topics/apf-topnews"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]


class RSSNewsIngestor(BaseIngestor):
    name = "RSS News"
    source = EventSource.RSS_NEWS
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        for feed_name, feed_url in RSS_FEEDS:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[:15]:
                    title = entry.get("title", "")
                    desc = entry.get("summary", entry.get("description", ""))
                    link = entry.get("link", "")

                    try:
                        if entry.get("published_parsed"):
                            ts = datetime(*entry.published_parsed[:6])
                        elif entry.get("published"):
                            ts = parsedate_to_datetime(entry.published)
                        else:
                            ts = datetime.utcnow()
                    except Exception:
                        ts = datetime.utcnow()

                    entities_found = extract_entities(title + " " + desc[:300])

                    events.append(GeoEvent(
                        source=EventSource.RSS_NEWS,
                        event_type=EventType.NEWS,
                        title=f"[{feed_name}] {title}",
                        description=desc[:500],
                        lat=None,
                        lon=None,
                        timestamp=ts,
                        entities=entities_found,
                        url=link,
                        metadata={"feed": feed_name, "feed_url": feed_url}
                    ))
            except Exception:
                continue
        return events
