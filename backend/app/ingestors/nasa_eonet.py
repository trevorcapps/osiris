import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


EVENT_TYPE_MAP = {
    "wildfires": EventType.WILDFIRE,
    "volcanoes": EventType.VOLCANO,
    "severeStorms": EventType.WEATHER,
    "earthquakes": EventType.EARTHQUAKE,
    "floods": EventType.NATURAL_DISASTER,
    "landslides": EventType.NATURAL_DISASTER,
    "seaAndLakeIce": EventType.NATURAL_DISASTER,
    "drought": EventType.NATURAL_DISASTER,
    "dustAndHaze": EventType.WEATHER,
    "tempExtremes": EventType.WEATHER,
    "waterColor": EventType.NATURAL_DISASTER,
    "manmade": EventType.INFRASTRUCTURE,
    "snow": EventType.WEATHER,
}


class NASAEONETIngestor(BaseIngestor):
    name = "NASA EONET"
    source = EventSource.NASA_EONET
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://eonet.gsfc.nasa.gov/api/v3/events",
                params={"limit": 50, "days": 7, "status": "open"}
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for ev in data.get("events", []):
                categories = [c.get("id", "") for c in ev.get("categories", [])]
                event_type = EventType.NATURAL_DISASTER
                for cat in categories:
                    if cat in EVENT_TYPE_MAP:
                        event_type = EVENT_TYPE_MAP[cat]
                        break

                # Get most recent geometry
                geometries = ev.get("geometry", [])
                if not geometries:
                    continue
                geo = geometries[-1]
                coords = geo.get("coordinates", [])
                if not coords or len(coords) < 2:
                    continue
                lon, lat = coords[0], coords[1]

                try:
                    ts = datetime.fromisoformat(geo.get("date", "").replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                events.append(GeoEvent(
                    source=EventSource.NASA_EONET,
                    event_type=event_type,
                    title=ev.get("title", "Natural Event"),
                    description=f"Categories: {', '.join(categories)}",
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    url=ev.get("link"),
                    metadata={
                        "eonet_id": ev.get("id"),
                        "categories": categories,
                        "sources": [s.get("url") for s in ev.get("sources", [])],
                    }
                ))
        return events
