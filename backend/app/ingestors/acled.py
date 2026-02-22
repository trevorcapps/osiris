import httpx
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities
from app.config import settings

LOGIN_URL = "https://acleddata.com/user/login?_format=json"
API_URL = "https://acleddata.com/api/acled/read"

logger = logging.getLogger(__name__)

# Cache session cookies across fetch cycles
_session_cookies: Optional[httpx.Cookies] = None


class ACLEDIngestor(BaseIngestor):
    name = "ACLED Conflict Data"
    source = EventSource.ACLED
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.acled_username and settings.acled_password)

    async def _login(self, client: httpx.AsyncClient) -> bool:
        global _session_cookies
        try:
            resp = await client.post(
                LOGIN_URL,
                json={
                    "name": settings.acled_username,
                    "pass": settings.acled_password,
                },
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                _session_cookies = resp.cookies
                logger.info("ACLED login successful")
                return True
            else:
                logger.error(f"ACLED login failed: {resp.status_code} {resp.text[:300]}")
                return False
        except Exception as e:
            logger.error(f"ACLED login error: {e}")
            return False

    async def fetch(self) -> List[GeoEvent]:
        global _session_cookies
        events = []
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            # Login if no cached session
            if not _session_cookies:
                if not await self._login(client):
                    return events

            # Set cookies on client
            client.cookies = _session_cookies

            resp = await client.get(
                API_URL,
                params={
                    "event_date": f"{week_ago}|",
                    "event_date_where": ">=",
                    "limit": 100,
                },
            )

            # If 403, try re-login once
            if resp.status_code == 403:
                logger.info("ACLED session expired, re-authenticating...")
                _session_cookies = None
                if not await self._login(client):
                    return events
                client.cookies = _session_cookies
                resp = await client.get(
                    API_URL,
                    params={
                        "event_date": f"{week_ago}|",
                        "event_date_where": ">=",
                        "limit": 100,
                    },
                )

            if resp.status_code != 200:
                logger.error(f"ACLED API request failed: {resp.status_code} {resp.text[:300]}")
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
