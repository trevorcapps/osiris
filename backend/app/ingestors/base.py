import logging
from abc import ABC, abstractmethod
from typing import List
from app.models.schemas import GeoEvent, EventSource

logger = logging.getLogger(__name__)


class BaseIngestor(ABC):
    name: str = "base"
    source: EventSource = None
    requires_key: bool = False

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if required API keys/config are present."""
        return True

    @abstractmethod
    async def fetch(self) -> List[GeoEvent]:
        """Fetch and return normalized GeoEvents."""
        return []

    async def safe_fetch(self) -> List[GeoEvent]:
        """Fetch with error handling."""
        if not self.is_configured():
            logger.info(f"{self.name}: not configured (missing API key)")
            return []
        try:
            events = await self.fetch()
            logger.info(f"{self.name}: fetched {len(events)} events")
            return events
        except Exception as e:
            logger.error(f"{self.name}: fetch failed — {e}")
            return []
