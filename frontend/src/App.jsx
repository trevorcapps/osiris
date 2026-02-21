import React, { useState, useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import { fetchEvents, searchEvents, getRelationships, getStats } from './services/api';
import { connect, subscribe, disconnect, subscribeStatus } from './services/websocket';
import LayerPanel from './components/LayerPanel';
import EntityDetail from './components/EntityDetail';
import RelationshipGraph from './components/RelationshipGraph';
import SearchBar from './components/SearchBar';
import StatsBar from './components/StatsBar';

const TYPE_COLORS_CSS = {
  conflict: '#ef4444', military: '#8b0000', aviation: '#06b6d4',
  maritime: '#3b82f6', earthquake: '#f97316', weather: '#fde68a',
  wildfire: '#ff4500', volcano: '#8b0000', natural_disaster: '#ff8c00',
  cyber: '#22c55e', infrastructure: '#9370db', sanctions: '#eab308',
  financial: '#adff2f', news: '#ffffff', humanitarian: '#ff69b4',
  health: '#00fa9a', terrorism: '#ef4444',
};

const SEVERITY_SCALE = { critical: 14, high: 11, medium: 8, low: 6 };

function cssToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return { r, g, b };
}

export default function App() {
  const [events, setEvents] = useState([]);
  const [filteredEvents, setFilteredEvents] = useState([]);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [relationships, setRelationships] = useState(null);
  const [stats, setStats] = useState(null);
  const [activeLayers, setActiveLayers] = useState(new Set(Object.keys(TYPE_COLORS_CSS)));
  const [activeSources, setActiveSources] = useState(new Set());
  const [showRelGraph, setShowRelGraph] = useState(false);
  const cesiumContainerRef = useRef(null);
  const viewerRef = useRef(null);
  const entitiesRef = useRef({});
  const [apiLastFetchAt, setApiLastFetchAt] = useState(null);
  const [apiEventCount, setApiEventCount] = useState(0);
  const [apiError, setApiError] = useState(null);
  const [wsState, setWsState] = useState('connecting');
  const [wsLastMessageAt, setWsLastMessageAt] = useState(null);
  const [wsEventCount, setWsEventCount] = useState(0);
  const [tileErrors, setTileErrors] = useState([]);
  const [showNonGeo, setShowNonGeo] = useState(false);

  // Initialize Cesium viewer
  useEffect(() => {
    if (!cesiumContainerRef.current || viewerRef.current) return;

    const ionToken = import.meta.env.VITE_CESIUM_ION_TOKEN;
    if (ionToken) {
      Cesium.Ion.defaultAccessToken = ionToken;
    } else {
      // Avoid noisy warnings when no token is configured.
      Cesium.Ion.defaultAccessToken = undefined;
    }

    const viewer = new Cesium.Viewer(cesiumContainerRef.current, {
      timeline: false,
      animation: false,
      homeButton: false,
      geocoder: false,
      sceneModePicker: false,
      baseLayerPicker: false,
      navigationHelpButton: false,
      fullscreenButton: false,
      selectionIndicator: false,
      infoBox: false,
      scene3DOnly: true,
      imageryProvider: ionToken
        ? Cesium.createWorldImagery({
          style: Cesium.IonWorldImageryStyle.AERIAL_WITH_LABELS,
        })
        : new Cesium.ArcGisMapServerImageryProvider({
          url: 'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer',
        }),
    });

    // Dark globe atmosphere
    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#0a0e17');
    if (viewer.scene.globe) {
      viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#1a1a2e');
    }
    if (viewer.scene.skyBox) viewer.scene.skyBox.show = true;
    if (viewer.scene.sun) viewer.scene.sun.show = false;
    if (viewer.scene.moon) viewer.scene.moon.show = false;

    // Click handler
    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id && picked.id._osirisEvent) {
        handleEventClick(picked.id._osirisEvent);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;
    const baseLayer = viewer.imageryLayers.get(0);
    const onTileError = (error) => {
      const message = error?.message || 'Tile load error';
      const label = `${new Date().toLocaleTimeString()} ${message}`;
      setTileErrors(prev => [label, ...prev].slice(0, 5));
    };
    if (baseLayer && baseLayer.errorEvent) {
      baseLayer.errorEvent.addEventListener(onTileError);
    }

    return () => {
      if (baseLayer && baseLayer.errorEvent) {
        baseLayer.errorEvent.removeEventListener(onTileError);
      }
      handler.destroy();
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  // Update entities on globe when filteredEvents change
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    // Clear existing
    viewer.entities.removeAll();

    filteredEvents.forEach(event => {
      if (!event.lat || !event.lon) return;
      const colorHex = TYPE_COLORS_CSS[event.event_type] || '#ffffff';
      const rgb = cssToRgb(colorHex);
      const size = SEVERITY_SCALE[event.severity] || 8;

      const entity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(event.lon, event.lat),
        point: {
          pixelSize: size,
          color: new Cesium.Color(rgb.r, rgb.g, rgb.b, 0.9),
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 1,
          scaleByDistance: new Cesium.NearFarScalar(1e3, 1.5, 1e7, 0.5),
        },
      });
      entity._osirisEvent = event;
    });
  }, [filteredEvents]);

  // Load data
  useEffect(() => {
    loadEvents();
    loadStats();
    connect();
    const unsubStatus = subscribeStatus((state) => setWsState(state));
    const unsub = subscribe((newEvents) => {
      setEvents(prev => {
        const seen = new Set();
        const merged = [];
        for (const ev of [...newEvents, ...prev]) {
          if (!ev || !ev.id || seen.has(ev.id)) continue;
          seen.add(ev.id);
          merged.push(ev);
          if (merged.length >= 10000) break;
        }
        return merged;
      });
      setWsLastMessageAt(Date.now());
      setWsEventCount(prev => prev + (newEvents?.length || 0));
    });
    const interval = setInterval(loadEvents, 300000);
    return () => { unsub(); unsubStatus(); disconnect(); clearInterval(interval); };
  }, []);

  // Filter
  useEffect(() => {
    const filtered = events.filter(e =>
      activeLayers.has(e.event_type) &&
      (activeSources.size === 0 || activeSources.has(e.source))
    );
    setFilteredEvents(filtered);
  }, [events, activeLayers, activeSources]);

  const geoStats = (() => {
    let geoCount = 0;
    let nonGeoCount = 0;
    const nonGeoByType = {};
    for (const e of filteredEvents) {
      if (e && e.lat != null && e.lon != null) {
        geoCount += 1;
      } else {
        nonGeoCount += 1;
        const t = e?.event_type || 'unknown';
        nonGeoByType[t] = (nonGeoByType[t] || 0) + 1;
      }
    }
    return { geoCount, nonGeoCount, nonGeoByType };
  })();

  const loadEvents = async () => {
    try {
      const data = await fetchEvents({ limit: 5000 });
      const incoming = data.events || [];
      if (incoming.length > 0) {
        setEvents(prev => {
          const seen = new Set();
          const merged = [];
          for (const ev of [...incoming, ...prev]) {
            if (!ev || !ev.id || seen.has(ev.id)) continue;
            seen.add(ev.id);
            merged.push(ev);
            if (merged.length >= 10000) break;
          }
          return merged;
        });
      }
      const sources = new Set(incoming.map(e => e.source));
      if (sources.size > 0) {
        setActiveSources(prev => {
          const next = new Set(prev);
          for (const s of sources) next.add(s);
          return next;
        });
      }
      setApiEventCount(incoming.length);
      setApiLastFetchAt(Date.now());
      setApiError(null);
    } catch (e) {
      console.error('Failed to load events:', e);
      setApiError(e);
      setApiLastFetchAt(Date.now());
    }
  };

  const loadStats = async () => {
    try { setStats(await getStats()); } catch (e) { console.error(e); }
  };

  const handleEventClick = async (event) => {
    setSelectedEvent(event);
    try {
      const rel = await getRelationships(event.id);
      setRelationships(rel);
    } catch (e) { setRelationships(null); }
  };

  const handleSearch = async (query) => {
    if (!query.trim()) { loadEvents(); return; }
    try {
      const data = await searchEvents({ query, limit: 200 });
      setFilteredEvents(data.results || []);
    } catch (e) { console.error('Search failed:', e); }
  };

  const handleFlyTo = (lat, lon) => {
    if (viewerRef.current) {
      viewerRef.current.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, 500000),
        duration: 1.5,
      });
    }
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
        pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
          <span style={{ fontSize: 24 }}>🌍</span>
          <h1 style={{ fontSize: 18, fontWeight: 700, letterSpacing: 2, color: '#60a5fa' }}>OSIRIS</h1>
        </div>
        <div style={{ pointerEvents: 'auto', flex: 1, maxWidth: 500 }}>
          <SearchBar onSearch={handleSearch} />
        </div>
        <div style={{ pointerEvents: 'auto' }}>
          <StatsBar stats={stats} />
        </div>
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

      {/* Status Panel */}
      <div style={{
        position: 'absolute',
        bottom: 16,
        left: 16,
        zIndex: 999,
        background: 'rgba(10,14,23,0.85)',
        border: '1px solid rgba(96,165,250,0.25)',
        borderRadius: 8,
        padding: '10px 12px',
        fontSize: 12,
        color: '#cbd5f5',
        minWidth: 220,
        pointerEvents: 'auto',
      }}>
        <div style={{ fontWeight: 600, marginBottom: 6, color: '#93c5fd' }}>Status</div>
        <div>Rendered events: {filteredEvents.length}</div>
        <div>With geo: {geoStats.geoCount}</div>
        <div>Without geo: {geoStats.nonGeoCount}</div>
        <div>API last fetch: {apiLastFetchAt ? new Date(apiLastFetchAt).toLocaleTimeString() : '—'}</div>
        <div>API events: {apiEventCount}{apiError ? ` (error)` : ''}</div>
        <div>WS state: {wsState}</div>
        <div>WS last msg: {wsLastMessageAt ? new Date(wsLastMessageAt).toLocaleTimeString() : '—'}</div>
        <div>WS events: {wsEventCount}</div>
        <div>Tile errors: {tileErrors.length}</div>
        {tileErrors.length > 0 && (
          <div style={{ marginTop: 6, color: '#fca5a5' }}>
            {tileErrors[0]}
          </div>
        )}
        {geoStats.nonGeoCount > 0 && (
          <div style={{ marginTop: 6 }}>
            <button
              onClick={() => setShowNonGeo(prev => !prev)}
              style={{
                background: 'rgba(96,165,250,0.15)',
                border: '1px solid rgba(96,165,250,0.3)',
                color: '#93c5fd',
                padding: '4px 6px',
                borderRadius: 6,
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              {showNonGeo ? 'Hide' : 'Show'} non-geo events
            </button>
          </div>
        )}
      </div>

      {/* Non-Geo Events Panel */}
      {showNonGeo && geoStats.nonGeoCount > 0 && (
        <div style={{
          position: 'absolute',
          bottom: 16,
          right: 16,
          zIndex: 999,
          background: 'rgba(10,14,23,0.9)',
          border: '1px solid rgba(96,165,250,0.25)',
          borderRadius: 8,
          padding: '10px 12px',
          width: 320,
          maxHeight: 260,
          overflow: 'auto',
          fontSize: 12,
          color: '#cbd5f5',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: '#93c5fd' }}>Non-Geo Events</div>
          <div style={{ marginBottom: 6, color: '#94a3b8' }}>
            By type: {Object.entries(geoStats.nonGeoByType).map(([k, v]) => `${k} ${v}`).join(' • ')}
          </div>
          {filteredEvents.filter(e => e && (e.lat == null || e.lon == null)).slice(0, 20).map((e) => (
            <div
              key={e.id}
              style={{
                padding: '6px 0',
                borderTop: '1px solid rgba(96,165,250,0.1)',
                cursor: 'pointer',
              }}
              onClick={() => handleEventClick(e)}
            >
              <div style={{ color: '#e2e8f0' }}>{e.title || 'Untitled'}</div>
              <div style={{ color: '#94a3b8' }}>{e.event_type} • {e.source}</div>
            </div>
          ))}
        </div>
      )}

      {/* Cesium Globe */}
      <div ref={cesiumContainerRef} style={{ width: '100%', height: '100%' }} />

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
