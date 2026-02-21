import logging
from typing import List, Optional, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, Range, models
)
from app.config import settings
from app.models.schemas import GeoEvent

logger = logging.getLogger(__name__)

COLLECTION_NAME = "osiris_events"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension


class VectorStore:
    def __init__(self):
        self.client = None

    async def connect(self):
        try:
            self.client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                timeout=10
            )
            # Create collection if not exists
            collections = self.client.get_collections().collections
            names = [c.name for c in collections]
            if COLLECTION_NAME not in names:
                self.client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=VECTOR_SIZE,
                        distance=Distance.COSINE
                    )
                )
                # Create payload indexes for filtering
                self.client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="source",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="event_type",
                    field_schema=models.PayloadSchemaType.KEYWORD
                )
                self.client.create_payload_index(
                    collection_name=COLLECTION_NAME,
                    field_name="timestamp",
                    field_schema=models.PayloadSchemaType.FLOAT
                )
                logger.info(f"Created Qdrant collection: {COLLECTION_NAME}")
            logger.info("Connected to Qdrant")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            self.client = None

    async def upsert_event(self, event: GeoEvent, embedding: List[float]):
        if not self.client:
            return
        try:
            payload = {
                "source": event.source.value,
                "event_type": event.event_type.value,
                "title": event.title,
                "description": event.description,
                "lat": event.lat,
                "lon": event.lon,
                "timestamp": event.timestamp.timestamp(),
                "entities": [e.model_dump() for e in event.entities],
                "metadata": event.metadata,
                "url": event.url,
                "severity": event.severity,
            }
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=event.id,
                    vector=embedding,
                    payload=payload
                )]
            )
        except Exception as e:
            logger.error(f"Failed to upsert event {event.id}: {e}")

    async def upsert_batch(self, events: List[GeoEvent], embeddings: List[List[float]]):
        if not self.client or not events:
            return
        try:
            points = []
            for event, embedding in zip(events, embeddings):
                payload = {
                    "source": event.source.value,
                    "event_type": event.event_type.value,
                    "title": event.title,
                    "description": event.description,
                    "lat": event.lat,
                    "lon": event.lon,
                    "timestamp": event.timestamp.timestamp(),
                    "entities": [e.model_dump() for e in event.entities],
                    "metadata": event.metadata,
                    "url": event.url,
                    "severity": event.severity,
                }
                points.append(PointStruct(
                    id=event.id,
                    vector=embedding,
                    payload=payload
                ))
            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=points
            )
            logger.info(f"Upserted {len(points)} events to Qdrant")
        except Exception as e:
            logger.error(f"Failed to batch upsert: {e}")

    async def search_similar(
        self,
        embedding: List[float],
        limit: int = 20,
        source_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
        time_range: Optional[tuple] = None,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        try:
            conditions = []
            if source_filter:
                conditions.append(FieldCondition(
                    key="source", match=MatchValue(value=source_filter)
                ))
            if type_filter:
                conditions.append(FieldCondition(
                    key="event_type", match=MatchValue(value=type_filter)
                ))
            if time_range:
                conditions.append(FieldCondition(
                    key="timestamp",
                    range=Range(gte=time_range[0], lte=time_range[1])
                ))

            query_filter = Filter(must=conditions) if conditions else None

            results = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=score_threshold
            )
            return [
                {"id": r.id, "score": r.score, **r.payload}
                for r in results
            ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    async def get_event_count(self) -> int:
        if not self.client:
            return 0
        try:
            info = self.client.get_collection(COLLECTION_NAME)
            return info.points_count
        except Exception:
            return 0


vector_store = VectorStore()
