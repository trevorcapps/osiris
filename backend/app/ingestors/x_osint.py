import feedparser
import httpx
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.ingestors.base import BaseIngestor
from app.models.schemas import EventSource, EventType, GeoEvent
from app.services.entity_extractor import extract_entities

logger = logging.getLogger(__name__)

# Public Nitter instances are hit-or-miss; keep multiple for fallback.
DEFAULT_NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.1d4.us",
]

DEFAULT_OSINT_HANDLES = [
    # General conflict / breaking
    "sentdefender",
    "AuroraIntel",
    "IntelCrab",
    "ELINTNews",
    "WarMonitors",
    # Maritime / air / tracking adjacent
    "MarineTraffic",
    "flightradar24",
    # Cyber / threat intel
    "vxunderground",
    "malwrhunterteam",
]


def _clean_handle(handle: str) -> str:
    return handle.strip().lstrip("@").lower()


class XOSINTIngestor(BaseIngestor):
    name = "X OSINT"
    source = EventSource.X_OSINT
    requires_key = False

    def __init__(self) -> None:
        super().__init__()
        default_handles_csv = ",".join(DEFAULT_OSINT_HANDLES)
        raw_handles = settings.x_osint_handles or default_handles_csv
        self.handles = [
            _clean_handle(h)
            for h in re.split(r"[,\s]+", raw_handles)
            if h and _clean_handle(h)
        ]

        raw_instances = settings.nitter_instances or ""
        parsed_instances = [
            i.strip().rstrip("/")
            for i in raw_instances.split(",")
            if i.strip()
        ]
        self.nitter_instances = parsed_instances or DEFAULT_NITTER_INSTANCES
        self._geocode_cache: Dict[str, Tuple[float, float]] = {}

    def is_configured(self) -> bool:
        return bool(self.handles)

    async def _geocode_text_location(
        self, client: httpx.AsyncClient, text: str
    ) -> Tuple[Optional[float], Optional[float]]:
        entities = extract_entities(text)
        location_entities = [e.name for e in entities if e.type in ("GPE", "LOC", "FAC")]

        for place in location_entities[:3]:  # keep requests bounded
            key = place.lower()
            if key in self._geocode_cache:
                lat, lon = self._geocode_cache[key]
                return lat, lon

            try:
                resp = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={"q": place, "format": "json", "limit": 1},
                    headers={"User-Agent": "osiris/0.1 (osint geocoder)"},
                )
                if resp.status_code != 200:
                    continue

                data = resp.json()
                if not data:
                    continue

                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                self._geocode_cache[key] = (lat, lon)
                return lat, lon
            except Exception:
                continue

        return None, None

    async def fetch(self) -> List[GeoEvent]:
        events: List[GeoEvent] = []

        if not self.handles:
            return events

        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            for handle in self.handles:
                feed_loaded = False

                for instance in self.nitter_instances:
                    feed_url = f"{instance}/{handle}/rss"
                    try:
                        resp = await client.get(
                            feed_url,
                            headers={
                                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
                                "Accept": "application/rss+xml,application/xml;q=0.9,*/*;q=0.8",
                            },
                        )
                        if resp.status_code != 200 or not resp.text:
                            continue

                        feed = feedparser.parse(resp.text)
                        if not feed.entries:
                            continue

                        for entry in feed.entries[:25]:
                            title = entry.get("title", "")
                            desc = entry.get("summary", entry.get("description", ""))
                            link = entry.get("link", f"https://x.com/{handle}")

                            try:
                                if entry.get("published_parsed"):
                                    ts = datetime(*entry.published_parsed[:6])
                                elif entry.get("published"):
                                    ts = parsedate_to_datetime(entry.published)
                                else:
                                    ts = datetime.utcnow()
                            except Exception:
                                ts = datetime.utcnow()

                            full_text = f"{title} {desc}".strip()
                            entities = extract_entities(full_text)
                            lat, lon = await self._geocode_text_location(client, full_text)

                            events.append(
                                GeoEvent(
                                    source=EventSource.X_OSINT,
                                    event_type=EventType.NEWS,
                                    title=f"[@{handle}] {title[:220]}",
                                    description=desc[:1200],
                                    lat=lat,
                                    lon=lon,
                                    timestamp=ts,
                                    entities=entities,
                                    url=link,
                                    metadata={
                                        "handle": handle,
                                        "feed_url": feed_url,
                                        "nitter_instance": instance,
                                    },
                                )
                            )

                        feed_loaded = True
                        break
                    except Exception as e:
                        logger.debug(
                            "X OSINT feed failed for @%s via %s: %s", handle, instance, e
                        )
                        continue

                if not feed_loaded:
                    logger.warning("Unable to fetch X OSINT feed for @%s", handle)

        return events
