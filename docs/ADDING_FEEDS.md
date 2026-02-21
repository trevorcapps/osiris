# Adding New OSINT Feeds

## 1. Create the Ingestor

Create a new file in `backend/app/ingestors/`:

```python
import httpx
from datetime import datetime
from typing import List
from app.ingestors.base import BaseIngestor
from app.models.schemas import GeoEvent, EventSource, EventType
from app.config import settings


class MyFeedIngestor(BaseIngestor):
    name = "My Feed"
    source = EventSource.MY_FEED  # Add to EventSource enum first
    requires_key = False  # Set True if API key needed

    def is_configured(self) -> bool:
        return True  # Or: return bool(settings.my_api_key)

    async def fetch(self) -> List[GeoEvent]:
        events = []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get("https://api.example.com/data")
            if resp.status_code != 200:
                return events
            for item in resp.json():
                events.append(GeoEvent(
                    source=EventSource.MY_FEED,
                    event_type=EventType.NEWS,  # Pick appropriate type
                    title=item["title"],
                    description=item.get("desc", ""),
                    lat=item.get("lat"),
                    lon=item.get("lon"),
                    timestamp=datetime.utcnow(),
                ))
        return events
```

## 2. Register the Source

Add to `EventSource` enum in `backend/app/models/schemas.py`:
```python
MY_FEED = "my_feed"
```

## 3. Register the Ingestor

In `backend/app/ingestors/registry.py`:
```python
from app.ingestors.my_feed import MyFeedIngestor
# Add to ALL_INGESTORS list
```

## 4. Add Config (if API key needed)

In `backend/app/config.py`:
```python
my_api_key: Optional[str] = None
```

And in `.env.example`:
```
MY_API_KEY=
```

That's it. The scheduler picks it up automatically on next cycle.
