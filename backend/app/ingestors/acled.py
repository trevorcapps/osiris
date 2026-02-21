import httpx
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.services.entity_extractor import extract_entities
from app.config import settings

TOKEN_URL = "https://acleddata.com/oauth/token"
API_URL = "https://acleddata.com/api/acled/read"
TOKEN_SKEW_SECONDS = 60
_token_cache = {
    "access_token": None,
    "refresh_token": None,
    "expires_at": 0.0,
}
logger = logging.getLogger(__name__)


class ACLEDIngestor(BaseIngestor):
    name = "ACLED Conflict Data"
    source = EventSource.ACLED
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.acled_refresh_token or (settings.acled_username and settings.acled_password))

    async def _fetch_token(self, client: httpx.AsyncClient) -> Optional[str]:
        now = time.time()
        if _token_cache["access_token"] and (_token_cache["expires_at"] - TOKEN_SKEW_SECONDS) > now:
            return _token_cache["access_token"]

        # Prefer refresh token if available
        if _token_cache["refresh_token"] or settings.acled_refresh_token:
            refresh_token = _token_cache["refresh_token"] or settings.acled_refresh_token
            resp = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": "acled",
                },
            )
        else:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "password",
                    "username": settings.acled_username,
                    "password": settings.acled_password,
                    "client_id": "acled",
                },
            )

        if resp.status_code != 200:
            logger.error(f"ACLED token request failed: {resp.status_code} {resp.text[:500]}")
            return None

        data = resp.json()
        access_token = data.get("access_token")
        if not access_token:
            logger.error("ACLED token response missing access_token")
            return None

        _token_cache["access_token"] = access_token
        _token_cache["refresh_token"] = data.get("refresh_token", _token_cache["refresh_token"])
        expires_in = int(data.get("expires_in", 0) or 0)
        _token_cache["expires_at"] = now + expires_in
        return access_token

    async def fetch(self) -> List[GeoEvent]:
        events = []
        week_ago = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._fetch_token(client)
            if not token:
                return events
            resp = await client.get(
                API_URL,
                params={
                    "event_date": f"{week_ago}|",
                    "event_date_where": ">=",
                    "limit": 100,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            if resp.status_code != 200:
                logger.error(f"ACLED API request failed: {resp.status_code} {resp.text[:500]}")
                return events
            data = resp.json()
            if data.get("status") not in (200, "200", None):
                logger.error(f"ACLED API returned non-200 status field: {data.get('status')} {str(data)[:500]}")
                return events
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
