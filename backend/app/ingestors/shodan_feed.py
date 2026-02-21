import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.config import settings


class ShodanIngestor(BaseIngestor):
    name = "Shodan"
    source = EventSource.SHODAN
    requires_key = True

    def is_configured(self) -> bool:
        return bool(settings.shodan_api_key)

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            # Search for interesting exposed services
            queries = [
                "industrial control system",
                "scada",
                "webcam has_screenshot:true",
            ]
            for q in queries[:1]:  # Rate limit — one query per fetch
                resp = await client.get(
                    "https://api.shodan.io/shodan/host/search",
                    params={"key": settings.shodan_api_key, "query": q, "page": 1}
                )
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for match in data.get("matches", [])[:30]:
                    lat = match.get("location", {}).get("latitude")
                    lon = match.get("location", {}).get("longitude")
                    ip = match.get("ip_str", "")
                    port = match.get("port", "")
                    product = match.get("product", "")

                    events.append(GeoEvent(
                        source=EventSource.SHODAN,
                        event_type=EventType.CYBER,
                        title=f"Exposed: {product or 'Service'} on {ip}:{port}",
                        description=match.get("data", "")[:300],
                        lat=lat,
                        lon=lon,
                        timestamp=datetime.utcnow(),
                        severity="high",
                        metadata={
                            "ip": ip,
                            "port": port,
                            "product": product,
                            "org": match.get("org"),
                            "os": match.get("os"),
                            "country": match.get("location", {}).get("country_name"),
                            "vulns": list(match.get("vulns", {}).keys()) if match.get("vulns") else [],
                        }
                    ))
        return events
