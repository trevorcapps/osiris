import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class USGSIngestor(BaseIngestor):
    name = "USGS Earthquakes"
    source = EventSource.USGS
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for feature in data.get("features", [])[:100]:
                props = feature.get("properties", {})
                coords = feature.get("geometry", {}).get("coordinates", [])
                lon = coords[0] if len(coords) > 0 else None
                lat = coords[1] if len(coords) > 1 else None
                mag = props.get("mag", 0)
                severity = "low"
                if mag and mag >= 6:
                    severity = "critical"
                elif mag and mag >= 4.5:
                    severity = "high"
                elif mag and mag >= 2.5:
                    severity = "medium"

                ts = datetime.utcfromtimestamp(props.get("time", 0) / 1000)
                events.append(GeoEvent(
                    source=EventSource.USGS,
                    event_type=EventType.EARTHQUAKE,
                    title=props.get("title", f"M{mag} Earthquake"),
                    description=f"Magnitude {mag} at depth {coords[2] if len(coords) > 2 else '?'}km",
                    lat=lat,
                    lon=lon,
                    timestamp=ts,
                    url=props.get("url"),
                    severity=severity,
                    metadata={
                        "magnitude": mag,
                        "depth_km": coords[2] if len(coords) > 2 else None,
                        "tsunami": props.get("tsunami", 0),
                        "felt": props.get("felt"),
                        "alert": props.get("alert"),
                        "place": props.get("place"),
                    }
                ))
        return events
