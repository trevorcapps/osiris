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
            # UNHCR Population API v1
            resp = await client.get(
                "https://api.unhcr.org/population/v1/countries/",
                params={"limit": 50}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for item in data.get("items", [])[:50]:
                country = item.get("name", "Unknown")
                code = item.get("iso2", "")
                region = item.get("region", "")

                events.append(GeoEvent(
                    source=EventSource.UNHCR,
                    event_type=EventType.HUMANITARIAN,
                    title=f"UNHCR Country Profile: {country}",
                    description=f"Region: {region}",
                    lat=None, lon=None,
                    timestamp=datetime.utcnow(),
                    severity="medium",
                    url=f"https://data.unhcr.org/en/country/{code.lower()}" if code else None,
                    metadata={
                        "country": country,
                        "iso": code,
                        "region": region,
                        "major_area": item.get("majorArea"),
                    }
                ))
        return events
