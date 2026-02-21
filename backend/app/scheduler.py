import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any
from app.ingestors.registry import ALL_INGESTORS
from app.services.vector_store import vector_store
from app.services.embeddings import embedding_service
from app.models.schemas import GeoEvent, FeedStatus

logger = logging.getLogger(__name__)

# In-memory event store (recent events for API access)
# Use a mutable container so all importers share the same reference.
_state: Dict[str, Any] = {
    "events": [],
    "feed_statuses": {},
    "ws_subscribers": [],
}

MAX_EVENTS = 10000


def get_event_store() -> List[GeoEvent]:
    return _state["events"]


def get_feed_statuses() -> Dict[str, FeedStatus]:
    return _state["feed_statuses"]


def register_ws(ws):
    _state["ws_subscribers"].append(ws)


def unregister_ws(ws):
    if ws in _state["ws_subscribers"]:
        _state["ws_subscribers"].remove(ws)


async def broadcast_events(events: List[GeoEvent]):
    subs = _state["ws_subscribers"]
    if not events or not subs:
        return
    import orjson
    payload = orjson.dumps([e.model_dump(mode="json") for e in events[:50]])
    dead = []
    for ws in subs:
        try:
            await ws.send_bytes(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        unregister_ws(ws)


async def run_ingestors():
    """Run all ingestors and store results."""
    logger.info("Starting ingestion cycle...")
    feed_statuses = _state["feed_statuses"]
    all_new_events = []

    for ingestor in ALL_INGESTORS:
        try:
            events = await ingestor.safe_fetch()
            if events:
                # Generate embeddings
                texts = [f"{e.title} {e.description}" for e in events]
                embeddings = embedding_service.embed_batch(texts)

                # Store in vector DB
                await vector_store.upsert_batch(events, embeddings)

                all_new_events.extend(events)

                feed_statuses[ingestor.name] = FeedStatus(
                    name=ingestor.name,
                    source=ingestor.source,
                    enabled=True,
                    configured=ingestor.is_configured(),
                    last_fetch=datetime.utcnow(),
                    event_count=len(events)
                )
            else:
                feed_statuses[ingestor.name] = FeedStatus(
                    name=ingestor.name,
                    source=ingestor.source,
                    enabled=True,
                    configured=ingestor.is_configured(),
                    last_fetch=datetime.utcnow(),
                    event_count=0
                )
        except Exception as e:
            logger.error(f"Ingestor {ingestor.name} failed: {e}")
            feed_statuses[ingestor.name] = FeedStatus(
                name=ingestor.name,
                source=ingestor.source,
                enabled=True,
                configured=ingestor.is_configured(),
                error=str(e)
            )

    # Update in-memory store
    _state["events"] = (all_new_events + _state["events"])[:MAX_EVENTS]
    logger.info(f"Ingestion complete: {len(all_new_events)} new events, {len(_state['events'])} total in memory")

    # Broadcast to WebSocket subscribers
    await broadcast_events(all_new_events)

    return all_new_events


async def scheduler_loop():
    """Background loop that runs ingestors periodically."""
    while True:
        try:
            await run_ingestors()
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(300)  # Every 5 minutes
