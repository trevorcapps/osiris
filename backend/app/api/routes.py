import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from app.models.schemas import (
    GeoEvent, GeoEventResponse, EventSource, EventType,
    SearchQuery, RelationshipResult, FeedStatus
)
from app.scheduler import get_event_store, get_feed_statuses, register_ws, unregister_ws, run_ingestors
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/events", response_model=GeoEventResponse)
async def get_events(
    source: Optional[EventSource] = None,
    event_type: Optional[EventType] = None,
    limit: int = Query(default=500, le=5000),
    offset: int = 0,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    since: Optional[str] = None,
):
    """Get events with optional filters."""
    filtered = get_event_store()
    if source:
        filtered = [e for e in filtered if e.source == source]
    if event_type:
        filtered = [e for e in filtered if e.event_type == event_type]
    if min_lat is not None:
        filtered = [e for e in filtered if e.lat and e.lat >= min_lat]
    if max_lat is not None:
        filtered = [e for e in filtered if e.lat and e.lat <= max_lat]
    if min_lon is not None:
        filtered = [e for e in filtered if e.lon and e.lon >= min_lon]
    if max_lon is not None:
        filtered = [e for e in filtered if e.lon and e.lon <= max_lon]
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            filtered = [e for e in filtered if e.timestamp >= since_dt]
        except ValueError:
            pass

    total = len(filtered)
    filtered = filtered[offset:offset + limit]

    sources_active = list(set(s.source.value for s in get_feed_statuses().values() if s.event_count > 0))
    sources_unavailable = list(set(s.source.value for s in get_feed_statuses().values() if not s.configured or s.error))

    return GeoEventResponse(
        events=filtered,
        total=total,
        sources_active=sources_active,
        sources_unavailable=sources_unavailable
    )


@router.post("/search")
async def search_events(query: SearchQuery):
    """Semantic search across all events via vector DB."""
    embedding = embedding_service.embed(query.query)
    source_filter = query.sources[0].value if query.sources and len(query.sources) == 1 else None
    type_filter = query.event_types[0].value if query.event_types and len(query.event_types) == 1 else None

    time_range = None
    if query.start_time and query.end_time:
        time_range = (query.start_time.timestamp(), query.end_time.timestamp())

    results = await vector_store.search_similar(
        embedding=embedding,
        limit=query.limit,
        source_filter=source_filter,
        type_filter=type_filter,
        time_range=time_range,
    )
    return {"results": results, "total": len(results)}


@router.get("/relationships/{event_id}")
async def get_relationships(event_id: str, limit: int = 20):
    """Find related events via vector similarity."""
    # Find the event in memory
    event = next((e for e in get_event_store() if e.id == event_id), None)
    if not event:
        return {"error": "Event not found", "related": []}

    # Embed and search
    text = f"{event.title} {event.description}"
    embedding = embedding_service.embed(text)
    related = await vector_store.search_similar(
        embedding=embedding,
        limit=limit + 1,  # +1 because it'll match itself
        score_threshold=0.3
    )
    # Filter out self
    related = [r for r in related if r["id"] != event_id][:limit]
    return {"event": event, "related": related}


@router.get("/feeds")
async def list_feed_statuses():
    """Get status of all feed ingestors."""
    from app.ingestors.registry import ALL_INGESTORS
    statuses = []
    for ingestor in ALL_INGESTORS:
        status = get_feed_statuses().get(ingestor.name, FeedStatus(
            name=ingestor.name,
            source=ingestor.source,
            enabled=True,
            configured=ingestor.is_configured()
        ))
        statuses.append(status)
    return {"feeds": statuses}


@router.post("/feeds/refresh")
async def refresh_feeds():
    """Manually trigger feed ingestion."""
    events = await run_ingestors()
    return {"message": f"Ingested {len(events)} events"}


@router.get("/entities")
async def search_entities(q: str, limit: int = 50):
    """Search entities across all events."""
    results = []
    seen = set()
    q_lower = q.lower()
    for event in get_event_store():
        for entity in event.entities:
            if q_lower in entity.name.lower() and entity.name not in seen:
                seen.add(entity.name)
                results.append({
                    "name": entity.name,
                    "type": entity.type,
                    "event_id": event.id,
                    "event_title": event.title,
                    "source": event.source.value,
                })
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break
    return {"entities": results, "total": len(results)}


@router.get("/stats")
async def get_stats():
    """Get platform statistics."""
    vector_count = await vector_store.get_event_count()
    source_counts = {}
    type_counts = {}
    for event in get_event_store():
        source_counts[event.source.value] = source_counts.get(event.source.value, 0) + 1
        type_counts[event.event_type.value] = type_counts.get(event.event_type.value, 0) + 1

    return {
        "total_events": len(get_event_store()),
        "vector_db_count": vector_count,
        "by_source": source_counts,
        "by_type": type_counts,
        "active_feeds": sum(1 for s in get_feed_statuses().values() if s.event_count > 0),
        "total_feeds": len(get_feed_statuses()),
    }
