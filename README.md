# 🌍 OSIRIS — Open Source Intelligence Reconnaissance & Insight System

A Google Earth-style 3D globe interface with real-time OSINT data feeds and AI-powered relationship mapping via vector database.

![License](https://img.shields.io/badge/license-MIT-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)

## Features

- **3D Globe** — CesiumJS-powered interactive globe with real-time data overlays
- **22 OSINT Feed Ingestors** — covering conflict, aviation, maritime, cyber, financial, humanitarian, and more
- **Vector DB Relationships** — Qdrant-powered semantic similarity finds non-obvious connections across data sources
- **Entity Extraction** — spaCy NER identifies people, organizations, and locations across all events
- **Real-time Updates** — WebSocket push for live data as feeds refresh
- **Relationship Graph** — vis.js force-directed graph visualization of entity connections
- **Layer Controls** — Toggle any event type on/off with live counts

## Data Sources

| Domain | Feeds |
|--------|-------|
| 🔴 Conflict | GDELT, ACLED, ReliefWeb |
| ✈️ Aviation | OpenSky Network |
| 🌍 Natural | USGS Earthquakes, NASA EONET, NOAA Weather, NASA FIRMS Wildfires, Smithsonian Volcanoes |
| 💻 Cyber | CISA KEV, Shodan, GreyNoise, AlienVault OTX |
| 🚫 Sanctions | OFAC SDN, OpenSanctions |
| 📰 News | RSS (Reuters, BBC, AP, Al Jazeera), X OSINT (configurable handles), Reddit |
| 🏥 Health | WHO Disease Outbreaks |
| 🤝 Humanitarian | UNHCR, ReliefWeb |
| 🏗️ Infrastructure | Submarine Cables (TeleGeography), IODA Internet Outages |

## Quick Start

```bash
# Clone
git clone https://github.com/trevorcapps/osiris.git
cd osiris

# Configure
cp .env.example .env
# Edit .env with your API keys (most feeds work without keys)
# Optional: customize X OSINT accounts
# X_OSINT_HANDLES=sentdefender,AuroraIntel,IntelCrab,ELINTNews,WarMonitors

# Launch
docker compose up -d

# Open
open http://localhost:3000
```

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│  CesiumJS   │◄────│   FastAPI    │◄────│  Qdrant  │
│  React SPA  │ WS  │   Backend    │     │ VectorDB │
└─────────────┘     └──────┬───────┘     └──────────┘
                           │
                    ┌──────┴───────┐
                    │  21 OSINT    │
                    │  Ingestors   │
                    │  (modular)   │
                    └──────────────┘
```

## Adding New Feeds

See [docs/ADDING_FEEDS.md](docs/ADDING_FEEDS.md) for the guide. TL;DR:

1. Create `backend/app/ingestors/your_feed.py`
2. Extend `BaseIngestor`, implement `fetch()` → returns `List[GeoEvent]`
3. Register in `backend/app/ingestors/registry.py`

## API

- `GET /api/events` — Get events with filters (source, type, bbox, time)
- `POST /api/search` — Semantic search via vector DB
- `GET /api/relationships/{event_id}` — Find related events
- `GET /api/entities?q=` — Search extracted entities
- `GET /api/feeds` — Feed ingestor statuses
- `POST /api/feeds/refresh` — Trigger manual refresh
- `GET /api/stats` — Platform statistics
- `WS /ws` — Real-time event stream

## Tech Stack

- **Frontend:** React + CesiumJS (resium) + vis-network
- **Backend:** Python FastAPI + spaCy + sentence-transformers
- **Vector DB:** Qdrant
- **Cache:** Redis
- **Container:** Docker Compose

## License

MIT
