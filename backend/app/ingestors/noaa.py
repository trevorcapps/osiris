import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class NOAAIngestor(BaseIngestor):
    name = "NOAA Weather Alerts"
    source = EventSource.NOAA
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.weather.gov/alerts/active",
                headers={"User-Agent": "OSIRIS OSINT Platform"}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for feature in data.get("features", [])[:75]:
                props = feature.get("properties", {})
                geo = feature.get("geometry")
                lat, lon = None, None
                if geo and geo.get("type") and geo.get("coordinates"):
                    coords = geo["coordinates"]
                    try:
                        if geo["type"] == "Point":
                            lon, lat = coords[0], coords[1]
                        elif geo["type"] == "Polygon" and coords and coords[0]:
                            ring = coords[0]
                            lat = sum(c[1] for c in ring) / len(ring)
                            lon = sum(c[0] for c in ring) / len(ring)
                    except (IndexError, TypeError):
                        lat, lon = None, None

                severity_map = {"Extreme": "critical", "Severe": "high", "Moderate": "medium", "Minor": "low"}
                severity = severity_map.get(props.get("severity"), "medium")

                try:
                    ts = datetime.fromisoformat(props.get("effective", "").replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                events.append(GeoEvent(
                    source=EventSource.NOAA,
                    event_type=EventType.WEATHER,
                    title=f"{props.get('event', 'Weather Alert')} — {props.get('areaDesc', '')}"[:200],
                    description=props.get("headline", "")[:500],
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    severity=severity,
                    url=props.get("id"),
                    metadata={
                        "event": props.get("event"),
                        "urgency": props.get("urgency"),
                        "certainty": props.get("certainty"),
                        "sender": props.get("senderName"),
                        "area": props.get("areaDesc"),
                    }
                ))
        return events
