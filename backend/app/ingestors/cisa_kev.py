import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType


class CISAKEVIngestor(BaseIngestor):
    name = "CISA KEV"
    source = EventSource.CISA_KEV
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
            )
            if resp.status_code != 200:
                return events
            data = resp.json()
            for vuln in data.get("vulnerabilities", [])[:50]:
                try:
                    ts = datetime.strptime(vuln.get("dateAdded", ""), "%Y-%m-%d")
                except (ValueError, TypeError):
                    ts = datetime.utcnow()

                cve = vuln.get("cveID", "Unknown")
                events.append(GeoEvent(
                    source=EventSource.CISA_KEV,
                    event_type=EventType.CYBER,
                    title=f"{cve}: {vuln.get('vulnerabilityName', '')}",
                    description=vuln.get("shortDescription", ""),
                    lat=38.8977,  # CISA HQ — Washington DC as default geo
                    lon=-77.0365,
                    timestamp=ts,
                    severity="critical",
                    url=f"https://nvd.nist.gov/vuln/detail/{cve}",
                    metadata={
                        "cve": cve,
                        "vendor": vuln.get("vendorProject"),
                        "product": vuln.get("product"),
                        "action": vuln.get("requiredAction"),
                        "due_date": vuln.get("dueDate"),
                        "known_ransomware": vuln.get("knownRansomwareCampaignUse"),
                    }
                ))
        return events
