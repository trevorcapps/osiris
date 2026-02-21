import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class UNHCRIngestor(BaseIngestor):
    name = "UNHCR Refugee Data"
    source = EventSource.UNHCR
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # UNHCR population statistics API
            resp = await client.get(
                "https://data.unhcr.org/api/population/get/timeseries",
                params={"limit": 50, "year": datetime.utcnow().year}
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("data", [])[:50]:
                    country = item.get("country_name", "Unknown")
                    refugees = item.get("refugees", 0)
                    events.append(GeoEvent(
                        source=EventSource.UNHCR,
                        event_type=EventType.HUMANITARIAN,
                        title=f"Refugee population: {country}",
                        description=f"Refugees: {refugees:,}",
                        lat=None, lon=None,
                        timestamp=datetime.utcnow(),
                        severity="high" if refugees and refugees > 100000 else "medium",
                        metadata={"country": country, "refugees": refugees}
                    ))

            # Also try situations API
            resp2 = await client.get("https://data.unhcr.org/api/situations")
            if resp2.status_code == 200:
                situations = resp2.json()
                for sit in (situations.get("data", []) if isinstance(situations, dict) else [])[:20]:
                    name = sit.get("name", "")
                    events.append(GeoEvent(
                        source=EventSource.UNHCR,
                        event_type=EventType.HUMANITARIAN,
                        title=f"UNHCR Situation: {name}",
                        description=str(sit.get("description", ""))[:500],
                        lat=None, lon=None,
                        timestamp=datetime.utcnow(),
                        severity="high",
                        metadata={"situation": name}
                    ))
        return events
