import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { Viewer, Entity, PointGraphics, CameraFlyTo, ImageryLayer } from 'resium';
import * as Cesium from 'cesium';
import { Color, Cartesian3, NearFarScalar, OpenStreetMapImageryProvider } from 'cesium';
import { fetchEvents, searchEvents, getRelationships, getStats, searchEntities } from './services/api';
import { connect, subscribe, disconnect } from './services/websocket';
import LayerPanel from './components/LayerPanel';
import EntityDetail from './components/EntityDetail';
import RelationshipGraph from './components/RelationshipGraph';
import SearchBar from './components/SearchBar';
import StatsBar from './components/StatsBar';

// Color mapping for event types
const TYPE_COLORS = {
  conflict: Color.RED,
  military: Color.DARKRED,
  aviation: Color.CYAN,
  maritime: Color.BLUE,
  earthquake: Color.ORANGE,
  weather: Color.LIGHTYELLOW,
  wildfire: Color.ORANGERED,
  volcano: Color.DARKRED,
  natural_disaster: Color.DARKORANGE,
  cyber: Color.LIME,
  infrastructure: Color.MEDIUMPURPLE,
  sanctions: Color.GOLD,
  financial: Color.GREENYELLOW,
  news: Color.WHITE,
  humanitarian: Color.HOTPINK,
  health: Color.MEDIUMSPRINGGREEN,
  terrorism: Color.RED,
};

const SEVERITY_SCALE = {
  critical: 14,
  high: 11,
  medium: 8,
  low: 6,
};

export default function App() {
  const [events, setEvents] = useState([]);
  const [filteredEvents, setFilteredEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [relationships, setRelationships] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeLayers, setActiveLayers] = useState(new Set(Object.keys(TYPE_COLORS)));
  const [activeSources, setActiveSources] = useState(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showRelGraph, setShowRelGraph] = useState(false);
  const [flyTo, setFlyTo] = useState(null);
  const viewerRef = useRef(null);

  const osmProvider = useMemo(() => new OpenStreetMapImageryProvider({
    url: 'https://tile.openstreetmap.org/',
  }), []);

  // Initial fetch
  useEffect(() => {
    loadEvents();
    loadStats();
    connect();
    const unsub = subscribe((newEvents) => {
      setEvents(prev => [...newEvents, ...prev].slice(0, 10000));
    });
    const interval = setInterval(loadEvents, 300000); // refresh every 5 min
    return () => { unsub(); disconnect(); clearInterval(interval); };
  }, []);

  // Filter events when layers change
  useEffect(() => {
    const filtered = events.filter(e =>
      activeLayers.has(e.event_type) &&
      (activeSources.size === 0 || activeSources.has(e.source))
    );
    setFilteredEvents(filtered);
  }, [events, activeLayers, activeSources]);

  const loadEvents = async () => {
    try {
      const data = await fetchEvents({ limit: 5000 });
      setEvents(data.events || []);
      // Auto-populate sources
      const sources = new Set((data.events || []).map(e => e.source));
      setActiveSources(sources);
    } catch (e) { console.error('Failed to load events:', e); }
  };

  const loadStats = async () => {
    try {
      const data = await getStats();
      setStats(data);
    } catch (e) { console.error('Failed to load stats:', e); }
  };

  const handleEventClick = async (event) => {
    setSelectedEvent(event);
    try {
      const rel = await getRelationships(event.id);
      setRelationships(rel);
    } catch (e) { setRelationships(null); }
  };

  const handleSearch = async (query) => {
    setSearchQuery(query);
    if (!query.trim()) {
      loadEvents();
      return;
    }
    try {
      const data = await searchEvents({ query, limit: 200 });
      const results = (data.results || []).map(r => ({
        ...r,
        id: r.id,
        lat: r.lat,
        lon: r.lon,
      }));
      setFilteredEvents(results);
    } catch (e) { console.error('Search failed:', e); }
  };

  const handleFlyTo = (lat, lon) => {
    setFlyTo({ lat, lon });
    setTimeout(() => setFlyTo(null), 2000);
  };

  const toggleLayer = (type) => {
    setActiveLayers(prev => {
      const next = new Set(prev);
      next.has(type) ? next.delete(type) : next.add(type);
      return next;
    });
  };

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative' }}>
      {/* Header */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1000,
        background: 'linear-gradient(180deg, rgba(10,14,23,0.95) 0%, rgba(10,14,23,0) 100%)',
        padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 16,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 24 }}>🌍</span>
          <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: 2, color: '#60a5fa' }}>OSIRIS</h1>
        </div>
        <SearchBar onSearch={handleSearch} />
        <StatsBar stats={stats} />
      </div>

      {/* Layer Panel */}
      <LayerPanel
        activeLayers={activeLayers}
        onToggle={toggleLayer}
        eventCounts={filteredEvents.reduce((acc, e) => {
          acc[e.event_type] = (acc[e.event_type] || 0) + 1;
          return acc;
        }, {})}
      />

      {/* Globe */}
      <Viewer
        ref={viewerRef}
        full
        timeline={false}
        animation={false}
        homeButton={false}
        geocoder={false}
        sceneModePicker={false}
        baseLayerPicker={false}
        navigationHelpButton={false}
        fullscreenButton={false}
        selectionIndicator={false}
        infoBox={false}
        scene3DOnly
        imageryProvider={osmProvider}
      >
        {flyTo && (
          <CameraFlyTo
            destination={Cartesian3.fromDegrees(flyTo.lon, flyTo.lat, 500000)}
            duration={1.5}
          />
        )}
        {filteredEvents.map(event => {
          if (!event.lat || !event.lon) return null;
          const color = TYPE_COLORS[event.event_type] || Color.WHITE;
          const size = SEVERITY_SCALE[event.severity] || 8;
          return (
            <Entity
              key={event.id}
              position={Cartesian3.fromDegrees(event.lon, event.lat)}
              name={event.title}
              description={event.description}
              onClick={() => handleEventClick(event)}
            >
              <PointGraphics
                pixelSize={size}
                color={color}
                outlineColor={Color.BLACK}
                outlineWidth={1}
                scaleByDistance={new NearFarScalar(1e3, 1.5, 1e7, 0.5)}
              />
            </Entity>
          );
        })}
      </Viewer>

      {/* Event Detail Panel */}
      {selectedEvent && (
        <EntityDetail
          event={selectedEvent}
          relationships={relationships}
          onClose={() => { setSelectedEvent(null); setRelationships(null); setShowRelGraph(false); }}
          onShowGraph={() => setShowRelGraph(true)}
          onFlyTo={handleFlyTo}
        />
      )}

      {/* Relationship Graph */}
      {showRelGraph && relationships && (
        <RelationshipGraph
          event={selectedEvent}
          relationships={relationships}
          onClose={() => setShowRelGraph(false)}
          onSelectEvent={handleEventClick}
        />
      )}
    </div>
  );
}
