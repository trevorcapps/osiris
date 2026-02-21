import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.config import settings


class OpenSkyIngestor(BaseIngestor):
    name = "OpenSky Network"
    source = EventSource.OPENSKY
    requires_key = False  # Works without auth, just rate-limited

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        auth = None
        if settings.opensky_username and settings.opensky_password:
            auth = (settings.opensky_username, settings.opensky_password)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://opensky-network.org/api/states/all",
                auth=auth
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            states = data.get("states", []) or []
            for state in states[:200]:  # Limit to 200 aircraft
                callsign = (state[1] or "").strip()
                lon = state[5]
                lat = state[6]
                alt = state[7]  # meters
                velocity = state[9]  # m/s
                heading = state[10]
                origin = state[2]  # origin country
                on_ground = state[8]

                if lat is None or lon is None or on_ground:
                    continue

                events.append(GeoEvent(
                    source=EventSource.OPENSKY,
                    event_type=EventType.AVIATION,
                    title=f"Aircraft {callsign or 'Unknown'}" + (f" ({origin})" if origin else ""),
                    description=f"Alt: {alt:.0f}m | Speed: {velocity:.0f}m/s | Heading: {heading:.0f}°" if alt and velocity and heading else "In flight",
                    lat=lat,
                    lon=lon,
                    timestamp=datetime.utcfromtimestamp(data.get("time", 0)),
                    metadata={
                        "icao24": state[0],
                        "callsign": callsign,
                        "origin_country": origin,
                        "altitude_m": alt,
                        "velocity_ms": velocity,
                        "heading": heading,
                        "on_ground": on_ground,
                        "squawk": state[14],
                    }
                ))
        return events
