# OSIRIS API Reference

Base URL: `http://localhost:8000`

## Endpoints

### GET /api/events
Get events with optional filters.

**Parameters:**
- `source` — Filter by EventSource enum value
- `event_type` — Filter by EventType enum value
- `limit` (default 500, max 5000)
- `offset` (default 0)
- `min_lat`, `max_lat`, `min_lon`, `max_lon` — Bounding box
- `since` — ISO datetime string

### POST /api/search
Semantic search via vector DB.

**Body:**
```json
{
  "query": "nuclear facility cyber attack",
  "sources": ["cisa_kev", "shodan"],
  "event_types": ["cyber"],
  "start_time": "2026-01-01T00:00:00",
  "end_time": "2026-02-21T00:00:00",
  "limit": 100
}
```

### GET /api/relationships/{event_id}
Find semantically related events.

**Parameters:**
- `limit` (default 20)

### GET /api/entities?q=
Search extracted entities by name.

### GET /api/feeds
Get status of all feed ingestors.

### POST /api/feeds/refresh
Manually trigger all feed ingestors.

### GET /api/stats
Platform statistics (counts, active feeds, etc).

### WS /ws
WebSocket for real-time event stream. New events pushed as JSON arrays.

### GET /health
Health check endpoint.
