import httpx
from datetime import datetime, timedelta
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class IODAIngestor(BaseIngestor):
    name = "IODA Internet Outages"
    source = EventSource.IODA
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        now = datetime.utcnow()
        since = int((now - timedelta(hours=24)).timestamp())
        until = int(now.timestamp())

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.ioda.inetintel.cc.gatech.edu/v2/alerts/country",
                params={"from": since, "until": until}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for alert in data.get("data", [])[:50]:
                entity = alert.get("entity", {})
                name = entity.get("name", "Unknown")
                code = entity.get("code", "")
                level = alert.get("level", "")
                condition = alert.get("condition", "")

                severity = "critical" if level == "critical" else "high" if level == "warning" else "medium"

                events.append(GeoEvent(
                    source=EventSource.IODA,
                    event_type=EventType.INFRASTRUCTURE,
                    title=f"Internet Outage: {name} ({code})",
                    description=f"Level: {level} | Condition: {condition}",
                    lat=None, lon=None,
                    timestamp=datetime.utcfromtimestamp(alert.get("time", 0)) if alert.get("time") else now,
                    severity=severity,
                    metadata={
                        "country": name,
                        "country_code": code,
                        "level": level,
                        "condition": condition,
                        "datasource": alert.get("datasource"),
                    }
                ))
        return events
