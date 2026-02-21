# OSIRIS Architecture

## Overview

OSIRIS is a containerized OSINT platform with four services:

1. **Frontend** — React SPA with CesiumJS 3D globe
2. **Backend** — FastAPI with modular feed ingestors
3. **Qdrant** — Vector database for semantic similarity
4. **Redis** — Caching layer

## Data Flow

1. **Ingestion** — APScheduler triggers all ingestors every 5 minutes
2. **Normalization** — Each ingestor outputs `GeoEvent` objects (common schema)
3. **Entity Extraction** — spaCy NER runs on all text fields
4. **Embedding** — sentence-transformers (all-MiniLM-L6-v2) encodes events
5. **Storage** — Events + embeddings upserted to Qdrant with metadata
6. **API** — FastAPI serves events, search, relationships via REST
7. **Real-time** — WebSocket pushes new events to connected clients
8. **Visualization** — CesiumJS renders points on 3D globe, vis.js renders relationship graphs

## GeoEvent Schema

All feeds normalize to this common schema:

```
{
  id: UUID
  source: EventSource (enum)
  event_type: EventType (enum)
  title: string
  description: string
  lat/lon: float (nullable)
  timestamp: datetime
  entities: [{name, type}]
  metadata: {any}
  severity: low|medium|high|critical
  url: string
}
```

## Vector Search

Events are embedded as `"{title} {description}"` using all-MiniLM-L6-v2 (384 dimensions). Qdrant stores these with metadata filters for source, type, and time range. Relationship queries find semantically similar events across all data sources.
