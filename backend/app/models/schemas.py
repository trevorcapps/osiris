from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class EventSource(str, Enum):
    GDELT = "gdelt"
    ACLED = "acled"
    UCDP = "ucdp"
    RELIEFWEB = "reliefweb"
    OPENSKY = "opensky"
    FAA_NOTAM = "faa_notam"
    AIS = "ais"
    NAVAREA = "navarea"
    USGS = "usgs"
    NASA_EONET = "nasa_eonet"
    NOAA = "noaa"
    NASA_FIRMS = "nasa_firms"
    VOLCANO = "volcano"
    SHODAN = "shodan"
    GREYNOISE = "greynoise"
    OTX = "otx"
    CISA_KEV = "cisa_kev"
    BGPSTREAM = "bgpstream"
    OFAC = "ofac"
    UN_SANCTIONS = "un_sanctions"
    EU_SANCTIONS = "eu_sanctions"
    OPENSANCTIONS = "opensanctions"
    SEC_EDGAR = "sec_edgar"
    WORLD_BANK = "world_bank"
    RSS_NEWS = "rss_news"
    REDDIT = "reddit"
    SUBMARINE_CABLES = "submarine_cables"
    IODA = "ioda"
    UNHCR = "unhcr"
    WHO = "who"
    INFORM_RISK = "inform_risk"


class EventType(str, Enum):
    CONFLICT = "conflict"
    MILITARY = "military"
    AVIATION = "aviation"
    MARITIME = "maritime"
    EARTHQUAKE = "earthquake"
    WEATHER = "weather"
    WILDFIRE = "wildfire"
    VOLCANO = "volcano"
    NATURAL_DISASTER = "natural_disaster"
    CYBER = "cyber"
    INFRASTRUCTURE = "infrastructure"
    SANCTIONS = "sanctions"
    FINANCIAL = "financial"
    NEWS = "news"
    HUMANITARIAN = "humanitarian"
    HEALTH = "health"
    TERRORISM = "terrorism"


class Entity(BaseModel):
    name: str
    type: str  # PERSON, ORG, GPE, LOC, VESSEL, AIRCRAFT, IP, etc.
    source_event_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GeoEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: EventSource
    event_type: EventType
    title: str
    description: str = ""
    lat: Optional[float] = None
    lon: Optional[float] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    entities: List[Entity] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    url: Optional[str] = None
    severity: Optional[str] = None  # low, medium, high, critical
    # Track geometry for moving objects
    geometry_type: str = "point"  # point, line, polygon
    coordinates: Optional[List] = None  # For complex geometries


class GeoEventResponse(BaseModel):
    events: List[GeoEvent]
    total: int
    sources_active: List[str]
    sources_unavailable: List[str]


class RelationshipResult(BaseModel):
    source_event: GeoEvent
    related_events: List[Dict[str, Any]]  # event + similarity score


class FeedStatus(BaseModel):
    name: str
    source: EventSource
    enabled: bool
    configured: bool  # Has required API keys
    last_fetch: Optional[datetime] = None
    event_count: int = 0
    error: Optional[str] = None


class SearchQuery(BaseModel):
    query: str
    sources: Optional[List[EventSource]] = None
    event_types: Optional[List[EventType]] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    bbox: Optional[List[float]] = None  # [min_lon, min_lat, max_lon, max_lat]
    limit: int = 100
