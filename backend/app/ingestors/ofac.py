import httpx
import csv
import io
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType, Entity


class OFACIngestor(BaseIngestor):
    name = "OFAC Sanctions"
    source = EventSource.OFAC
    requires_key = False

    def is_configured(self) -> bool:
        return True

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=60) as client:
            # OFAC SDN list in CSV
            resp = await client.get(
                "https://www.treasury.gov/ofac/downloads/sdn.csv"
            )
            if resp.status_code != 200:
                return events
            reader = csv.reader(io.StringIO(resp.text))
            count = 0
            for row in reader:
                if count >= 100 or len(row) < 4:
                    break
                ent_num = row[0].strip()
                name = row[1].strip()
                sdn_type = row[2].strip()
                program = row[3].strip()
                remarks = row[5].strip() if len(row) > 5 else ""

                if not name:
                    continue

                entity_type = "PERSON" if sdn_type == "individual" else "ORG"

                events.append(GeoEvent(
                    source=EventSource.OFAC,
                    event_type=EventType.SANCTIONS,
                    title=f"OFAC SDN: {name}",
                    description=f"Type: {sdn_type} | Program: {program} | {remarks}"[:500],
                    lat=38.8977,
                    lon=-77.0365,  # DC
                    timestamp=datetime.utcnow(),
                    entities=[Entity(name=name, type=entity_type)],
                    severity="high",
                    metadata={
                        "sdn_number": ent_num,
                        "sdn_type": sdn_type,
                        "program": program,
                        "remarks": remarks,
                    }
                ))
                count += 1
        return events
