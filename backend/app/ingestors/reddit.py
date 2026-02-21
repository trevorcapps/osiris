import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities

SUBREDDITS = [
    "worldnews",
    "geopolitics",
    "cybersecurity",
    "netsec",
    "intelligence",
]


class RedditIngestor(BaseIngestor):
    name = "Reddit"
    source = EventSource.REDDIT
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30, headers={"User-Agent": "OSIRIS/1.0"}) as client:
            for sub in SUBREDDITS:
                try:
                    resp = await client.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=10")
                    if resp.status_code != 200:
                        continue
                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        d = post.get("data", {})
                        title = d.get("title", "")
                        selftext = d.get("selftext", "")[:300]
                        url = d.get("url", "")
                        score = d.get("score", 0)

                        ts = datetime.utcfromtimestamp(d.get("created_utc", 0))
                        entities_found = extract_entities(title)

                        events.append(GeoEvent(
                            source=EventSource.REDDIT,
                            event_type=EventType.NEWS,
                            title=f"r/{sub}: {title}",
                            description=selftext,
                            lat=None,
                            lon=None,
                            timestamp=ts,
                            entities=entities_found,
                            url=f"https://reddit.com{d.get('permalink', '')}",
                            metadata={
                                "subreddit": sub,
                                "score": score,
                                "num_comments": d.get("num_comments", 0),
                                "author": d.get("author"),
                                "external_url": url if not url.startswith("https://www.reddit.com") else None,
                            }
                        ))
                except Exception:
                    continue
        return events
