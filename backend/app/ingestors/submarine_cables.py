import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class SubmarineCableIngestor(BaseIngestor):
    name = "Submarine Cables"
    source = EventSource.SUBMARINE_CABLES
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # TeleGeography submarine cable API
            resp = await client.get("https://www.submarinecablemap.com/api/v3/cable/all.json")
            if resp.status_code != 200:
                return events
            cables = resp.json()
            for cable in cables[:100]:
                name = cable.get("name", "Unknown Cable")
                landing_points = cable.get("landing_points", [])
                rfs = cable.get("rfs", "")
                length_km = cable.get("length", "")
                owners = cable.get("owners", "")

                # Use first landing point for geo
                lat, lon = None, None
                if landing_points:
                    lp = landing_points[0]
                    if isinstance(lp, dict):
                        lat = lp.get("latitude")
                        lon = lp.get("longitude")

                events.append(GeoEvent(
                    source=EventSource.SUBMARINE_CABLES,
                    event_type=EventType.INFRASTRUCTURE,
                    title=f"Submarine Cable: {name}",
                    description=f"Length: {length_km}km | RFS: {rfs} | Landing points: {len(landing_points)}",
                    lat=lat,
                    lon=lon,
                    timestamp=datetime.utcnow(),
                    metadata={
                        "cable_name": name,
                        "rfs": rfs,
                        "length_km": length_km,
                        "owners": owners,
                        "landing_point_count": len(landing_points),
                    },
                    geometry_type="line" if len(landing_points) > 1 else "point"
                ))
        return events
