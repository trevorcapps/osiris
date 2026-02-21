import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.config import settings


class OTXIngestor(BaseIngestor):
    name = "AlienVault OTX"
    source = EventSource.OTX
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.otx_api_key)

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://otx.alienvault.com/api/v1/pulses/subscribed",
                params={"limit": 30, "modified_since": ""},
                headers={"X-OTX-API-KEY": settings.otx_api_key}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for pulse in data.get("results", []):
                title = pulse.get("name", "Unknown Pulse")
                desc = pulse.get("description", "")
                tags = pulse.get("tags", [])
                indicators = pulse.get("indicators", [])

                try:
                    ts = datetime.fromisoformat(pulse.get("modified", "").replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                # Try to find geo from indicators
                lat, lon = None, None
                ioc_types = set()
                for ind in indicators[:20]:
                    ioc_types.add(ind.get("type", ""))

                events.append(GeoEvent(
                    source=EventSource.OTX,
                    event_type=EventType.CYBER,
                    title=title,
                    description=desc[:500],
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    severity="high",
                    url=f"https://otx.alienvault.com/pulse/{pulse.get('id', '')}",
                    metadata={
                        "pulse_id": pulse.get("id"),
                        "tags": tags,
                        "ioc_count": len(indicators),
                        "ioc_types": list(ioc_types),
                        "tlp": pulse.get("tlp", "white"),
                        "adversary": pulse.get("adversary"),
                    }
                ))
        return events
