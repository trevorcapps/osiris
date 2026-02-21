import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.config import settings


class GreyNoiseIngestor(BaseIngestor):
    name = "GreyNoise"
    source = EventSource.GREYNOISE
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.greynoise_api_key)

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.greynoise.io/v3/community/search",
                params={"query": "classification:malicious", "limit": 50},
                headers={"key": settings.greynoise_api_key}
            )
            if resp.status_code != 200:
                # Try community endpoint
                resp = await client.get(
                    "https://api.greynoise.io/v3/community/1.1.1.1",
                    headers={"key": settings.greynoise_api_key}
                )
                return events
            data = resp.json()
            for item in data.get("data", []):
                ip = item.get("ip", "")
                lat = item.get("metadata", {}).get("latitude")
                lon = item.get("metadata", {}).get("longitude")
                classification = item.get("classification", "unknown")

                severity = "critical" if classification == "malicious" else "medium"

                events.append(GeoEvent(
                    source=EventSource.GREYNOISE,
                    event_type=EventType.CYBER,
                    title=f"Threat IP: {ip} ({classification})",
                    description=f"ASN: {item.get('metadata', {}).get('asn', 'N/A')} | OS: {item.get('metadata', {}).get('os', 'N/A')}",
                    lat=lat,
                    lon=lon,
                    timestamp=datetime.utcnow(),
                    severity=severity,
                    metadata={
                        "ip": ip,
                        "classification": classification,
                        "tags": item.get("tags", []),
                        "vpn": item.get("vpn"),
                        "bot": item.get("bot"),
                        "asn": item.get("metadata", {}).get("asn"),
                        "city": item.get("metadata", {}).get("city"),
                        "country": item.get("metadata", {}).get("country"),
                    }
                ))
        return events
