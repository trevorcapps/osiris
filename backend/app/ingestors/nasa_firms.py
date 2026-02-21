import httpx
import csv
import io
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class NASAFIRMSIngestor(BaseIngestor):
    name = "NASA FIRMS Wildfires"
    source = EventSource.NASA_FIRMS
    requires_key = False  # CSV feed is public

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        # MODIS/VIIRS active fire data — last 24h, global CSV
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(
                "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_Global_24h.csv"
            )
            if resp.status_code != 200:
                return events
            reader = csv.DictReader(io.StringIO(resp.text))
            count = 0
            for row in reader:
                if count >= 200:  # Limit
                    break
                try:
                    lat = float(row.get("latitude", 0))
                    lon = float(row.get("longitude", 0))
                    confidence = row.get("confidence", "0")
                    brightness = row.get("brightness", "")
                    acq_date = row.get("acq_date", "")
                    acq_time = row.get("acq_time", "0000")

                    # Only high-confidence fires
                    conf_val = int(confidence) if confidence.isdigit() else 0
                    if conf_val < 50:
                        continue

                    ts = datetime.strptime(f"{acq_date} {acq_time}", "%Y-%m-%d %H%M")
                    severity = "high" if conf_val >= 80 else "medium"

                    events.append(GeoEvent(
                        source=EventSource.NASA_FIRMS,
                        event_type=EventType.WILDFIRE,
                        title=f"Active Fire Detection ({confidence}% confidence)",
                        description=f"Brightness: {brightness}K | FRP: {row.get('frp', 'N/A')}MW",
                        lat=lat,
                        lon=lon,
                        timestamp=ts,
                        severity=severity,
                        metadata={
                            "brightness": brightness,
                            "confidence": confidence,
                            "frp": row.get("frp"),
                            "satellite": row.get("satellite"),
                            "daynight": row.get("daynight"),
                        }
                    ))
                    count += 1
                except (ValueError, KeyError):
                    continue
        return events
