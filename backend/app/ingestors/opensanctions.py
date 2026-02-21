import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType, Entity


class OpenSanctionsIngestor(BaseIngestor):
    name = "OpenSanctions"
    source = EventSource.OPENSANCTIONS
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # OpenSanctions API — recent additions
            resp = await client.get(
                "https://api.opensanctions.org/search/default",
                params={"q": "*", "limit": 50},
                headers={"Accept": "application/json"}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for result in data.get("results", []):
                name = result.get("caption", "Unknown Entity")
                schema = result.get("schema", "")
                datasets = result.get("datasets", [])
                countries = result.get("properties", {}).get("country", [])
                entity_type = "PERSON" if schema == "Person" else "ORG"

                events.append(GeoEvent(
                    source=EventSource.OPENSANCTIONS,
                    event_type=EventType.SANCTIONS,
                    title=f"Sanctioned: {name}",
                    description=f"Schema: {schema} | Datasets: {', '.join(datasets)}",
                    lat=None,
                    lon=None,
                    timestamp=datetime.utcnow(),
                    entities=[Entity(name=name, type=entity_type)],
                    severity="high",
                    metadata={
                        "opensanctions_id": result.get("id"),
                        "schema": schema,
                        "datasets": datasets,
                        "countries": countries,
                    }
                ))
        return events
