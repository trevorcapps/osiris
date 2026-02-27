import React, { useState, useEffect, useRef, useMemo } from 'react';
import * as Cesium from 'cesium';
import { fetchEvents, searchEvents, getRelationships, getStats } from './services/api';
import { connect, subscribe, disconnect, subscribeStatus } from './services/websocket';
import LayerPanel from './components/LayerPanel';
import EntityDetail from './components/EntityDetail';
import RelationshipGraph from './components/RelationshipGraph';
import SearchBar from './components/SearchBar';
import StatsBar from './components/StatsBar';

const TYPE_COLORS_CSS = {
  conflict: '#ff4d6d', military: '#f43f5e', aviation: '#22d3ee',
  maritime: '#60a5fa', earthquake: '#fb923c', weather: '#facc15',
  wildfire: '#f97316', volcano: '#dc2626', natural_disaster: '#fb7185',
  cyber: '#f472b6', infrastructure: '#a78bfa', sanctions: '#fde047',
  financial: '#84cc16', news: '#f8fafc', humanitarian: '#f472b6',
  health: '#2dd4bf', terrorism: '#ef4444',
};

const SEVERITY_SCALE = { critical: 16, high: 12, medium: 9, low: 7 };
const SEVERITY_SPEED = { critical: 2.6, high: 2.0, medium: 1.5, low: 1.1 };
const TIME_WINDOWS = {
  live: null,
  '1m': 60 * 1000,
  '5m': 5 * 60 * 1000,
  '1h': 60 * 60 * 1000,
};

function cssToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  return { r, g, b };
}

function eventTs(event) {
  const ts = event?.timestamp || event?.published_at || event?.created_at;
  const parsed = ts ? new Date(ts).getTime() : 0;
  return Number.isFinite(parsed) ? parsed : 0;
}

function ageState(ageSec) {
  if (ageSec < 20) return 'new';
  if (ageSec < 180) return 'active';
  return 'cooling';
}

function formatGridRegion(lat, lon) {
  const latBand = Math.round(lat / 20) * 20;
  const lonBand = Math.round(lon / 20) * 20;
  const latLabel = `${latBand >= 0 ? 'N' : 'S'}${Math.abs(latBand)}`;
  const lonLabel = `${lonBand >= 0 ? 'E' : 'W'}${Math.abs(lonBand)}`;
  return `${latLabel} ${lonLabel}`;
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
  const [timeWindow, setTimeWindow] = useState('live');
  const [isPaused, setIsPaused] = useState(false);
  const [replayCursor, setReplayCursor] = useState(null);
  const [feedRail, setFeedRail] = useState([]);

  const cesiumContainerRef = useRef(null);
  const viewerRef = useRef(null);

  const [apiLastFetchAt, setApiLastFetchAt] = useState(null);
  const [apiEventCount, setApiEventCount] = useState(0);
  const [apiError, setApiError] = useState(null);
  const [wsState, setWsState] = useState('connecting');
  const [wsLastMessageAt, setWsLastMessageAt] = useState(null);
  const [wsEventCount, setWsEventCount] = useState(0);
  const [tileErrors, setTileErrors] = useState([]);
  const [showNonGeo, setShowNonGeo] = useState(false);
  const [tilesetStatus, setTilesetStatus] = useState('earth-at-night (loading)');

  const timelineBounds = useMemo(() => {
    const timestamps = events.map(eventTs).filter(Boolean);
    if (!timestamps.length) return { min: 0, max: 0 };
    return { min: Math.min(...timestamps), max: Math.max(...timestamps) };
  }, [events]);

  const timelineNow = isPaused && replayCursor ? replayCursor : Date.now();

  const enqueueFeed = (incoming) => {
    if (!incoming?.length) return;
    const grouped = new Map();
    for (const ev of incoming) {
      const key = `${ev.event_type || 'unknown'}::${ev.severity || 'medium'}::${ev.source || 'src'}`;
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key).push(ev);
    }

    const rows = Array.from(grouped.values()).map(group => {
      const sample = group[0];
      const count = group.length;
      const label = count > 1
        ? `+${count} ${sample.event_type || 'event'} events (${sample.source || 'unknown'} burst)`
        : (sample.title || `${sample.event_type || 'event'} update`);
      return {
        id: `${sample.id}-${Date.now()}-${Math.random()}`,
        ts: Date.now(),
        count,
        label,
        event: sample,
      };
    });

    setFeedRail(prev => [...rows, ...prev].slice(0, 80));
  };

  useEffect(() => {
    if (!cesiumContainerRef.current || viewerRef.current) return;

    const ionToken = import.meta.env.VITE_CESIUM_ION_TOKEN;
    if (ionToken) {
      Cesium.Ion.defaultAccessToken = ionToken;
    } else {
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
      imageryProvider: new Cesium.ArcGisMapServerImageryProvider({
        url: 'https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer',
      }),
    });

    let baseLayer = viewer.imageryLayers.get(0);
    const applyLayerStyle = (layer) => {
      if (!layer) return;
      layer.brightness = 0.45;
      layer.contrast = 1.15;
      layer.saturation = 0.1;
      layer.hue = 0.58;
      layer.gamma = 0.9;
    };
    applyLayerStyle(baseLayer);

    const onTileError = (error) => {
      const message = error?.message || 'Tile load error';
      const label = `${new Date().toLocaleTimeString()} ${message}`;
      setTileErrors(prev => [label, ...prev].slice(0, 5));
    };

    const loadEarthAtNight = async () => {
      if (!ionToken || !Cesium.IonImageryProvider?.fromAssetId) {
        setTilesetStatus('fallback-dark-gray');
        return;
      }
      try {
        const provider = await Cesium.IonImageryProvider.fromAssetId(3812);
        viewer.imageryLayers.removeAll();
        baseLayer = viewer.imageryLayers.addImageryProvider(provider);
        applyLayerStyle(baseLayer);
        if (baseLayer?.errorEvent) baseLayer.errorEvent.addEventListener(onTileError);
        setTilesetStatus('earth-at-night (ion:3812)');
      } catch (e) {
        console.error('Failed to load Earth at Night imagery:', e);
        setTilesetStatus('imagery-error-fallback');
      }
    };

    viewer.scene.backgroundColor = Cesium.Color.fromCssColorString('#030712');
    if (viewer.scene.globe) {
      viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#020617');
      viewer.scene.globe.showGroundAtmosphere = false;
      viewer.scene.fog.enabled = false;
    }
    viewer.scene.highDynamicRange = true;
    if (viewer.scene.skyBox) viewer.scene.skyBox.show = true;
    if (viewer.scene.sun) viewer.scene.sun.show = false;
    if (viewer.scene.moon) viewer.scene.moon.show = false;

    const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    handler.setInputAction((click) => {
      const picked = viewer.scene.pick(click.position);
      if (Cesium.defined(picked) && picked.id && picked.id._osirisEvent) {
        handleEventClick(picked.id._osirisEvent);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;

    if (baseLayer?.errorEvent) baseLayer.errorEvent.addEventListener(onTileError);
    loadEarthAtNight();

    return () => {
      if (baseLayer?.errorEvent) baseLayer.errorEvent.removeEventListener(onTileError);
      handler.destroy();
      viewer.destroy();
      viewerRef.current = null;
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    viewer.entities.removeAll();

    const now = timelineNow;
    const geoEvents = filteredEvents.filter(e => e.lat != null && e.lon != null).slice(0, 2500);

    geoEvents.forEach((event) => {
      const colorHex = TYPE_COLORS_CSS[event.event_type] || '#f8fafc';
      const rgb = cssToRgb(colorHex);
      const baseSize = SEVERITY_SCALE[event.severity] || 9;
      const ts = eventTs(event) || now;

      const pointColor = new Cesium.CallbackProperty(() => {
        const ageSec = Math.max(0, (now - ts) / 1000);
        const state = ageState(ageSec);
        const pulse = 0.5 + 0.5 * Math.sin(Date.now() / 180);
        if (state === 'new') return new Cesium.Color(rgb.r, rgb.g, rgb.b, 0.95);
        if (state === 'active') return new Cesium.Color(rgb.r, rgb.g, rgb.b, 0.65 + 0.25 * pulse);
        return new Cesium.Color(rgb.r * 0.9, rgb.g * 0.9, rgb.b * 0.9, 0.28);
      }, false);

      const pointSize = new Cesium.CallbackProperty(() => {
        const ageSec = Math.max(0, (now - ts) / 1000);
        const state = ageState(ageSec);
        const speed = SEVERITY_SPEED[event.severity] || 1.4;
        const wave = 0.7 + Math.abs(Math.sin(Date.now() / (240 / speed)));
        if (state === 'new') return baseSize + 5 * wave;
        if (state === 'active') return baseSize + 2 * wave;
        return Math.max(4, baseSize - 2);
      }, false);

      const entity = viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(event.lon, event.lat),
        point: {
          pixelSize: pointSize,
          color: pointColor,
          outlineColor: Cesium.Color.fromCssColorString('#fef08a'),
          outlineWidth: 0.9,
          scaleByDistance: new Cesium.NearFarScalar(1e3, 1.4, 1e7, 0.4),
        },
      });
      entity._osirisEvent = event;

      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(event.lon, event.lat),
        ellipse: {
          semiMinorAxis: new Cesium.CallbackProperty(() => {
            const ageSec = Math.max(0, (now - ts) / 1000);
            if (ageSec > 20) return 0;
            return 3000 + ageSec * 600;
          }, false),
          semiMajorAxis: new Cesium.CallbackProperty(() => {
            const ageSec = Math.max(0, (now - ts) / 1000);
            if (ageSec > 20) return 0;
            return 3000 + ageSec * 600;
          }, false),
          material: new Cesium.ColorMaterialProperty(new Cesium.CallbackProperty(() => {
            const ageSec = Math.max(0, (now - ts) / 1000);
            const alpha = Math.max(0, 0.35 - ageSec / 65);
            return new Cesium.Color(rgb.r, rgb.g, rgb.b, alpha);
          }, false)),
          height: 0,
        },
      });
    });

    const recentGeo = geoEvents
      .filter(e => Math.max(0, (now - eventTs(e)) / 1000) < 3600)
      .sort((a, b) => eventTs(b) - eventTs(a))
      .slice(0, 240);

    const links = [];
    const bySource = new Map();
    for (const ev of recentGeo) {
      const key = ev.source || 'unknown';
      if (!bySource.has(key)) bySource.set(key, []);
      bySource.get(key).push(ev);
    }

    bySource.forEach((arr) => {
      for (let i = 1; i < arr.length && links.length < 100; i += 1) {
        const a = arr[i - 1];
        const b = arr[i];
        links.push({ from: a, to: b });
      }
    });

    links.forEach((link) => {
      const colorHex = TYPE_COLORS_CSS[link.from.event_type] || '#f472b6';
      const rgb = cssToRgb(colorHex);
      const speed = SEVERITY_SPEED[link.from.severity] || 1.4;
      const from = Cesium.Cartesian3.fromDegrees(link.from.lon, link.from.lat);
      const to = Cesium.Cartesian3.fromDegrees(link.to.lon, link.to.lat);

      viewer.entities.add({
        polyline: {
          positions: [from, to],
          width: 1.2,
          material: new Cesium.PolylineGlowMaterialProperty({
            glowPower: 0.12,
            taperPower: 0.5,
            color: new Cesium.Color(rgb.r, rgb.g, rgb.b, 0.3),
          }),
          arcType: Cesium.ArcType.GEODESIC,
          clampToGround: false,
        },
      });

      viewer.entities.add({
        position: new Cesium.CallbackProperty(() => {
          const t = (Date.now() / (1800 / speed)) % 1;
          return Cesium.Cartesian3.lerp(from, to, t, new Cesium.Cartesian3());
        }, false),
        point: {
          pixelSize: 3,
          color: new Cesium.Color(rgb.r, rgb.g, rgb.b, 0.9),
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 0.5,
        },
      });
    });
  }, [filteredEvents, timelineNow]);

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

      const sources = new Set((newEvents || []).map(e => e?.source).filter(Boolean));
      if (sources.size > 0) {
        setActiveSources(prev => {
          const next = new Set(prev);
          for (const s of sources) next.add(s);
          return next;
        });
      }
      enqueueFeed(newEvents || []);
      setWsLastMessageAt(Date.now());
      setWsEventCount(prev => prev + (newEvents?.length || 0));
    });

    const interval = setInterval(loadEvents, 300000);
    return () => {
      unsub();
      unsubStatus();
      disconnect();
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const maxNow = isPaused && replayCursor ? replayCursor : Date.now();
    const windowMs = TIME_WINDOWS[timeWindow];

    const filtered = events.filter((e) => {
      if (!activeLayers.has(e.event_type)) return false;
      if (activeSources.size > 0 && !activeSources.has(e.source)) return false;
      if (!windowMs) return true;
      const ts = eventTs(e);
      return ts && ts <= maxNow && ts >= maxNow - windowMs;
    });

    setFilteredEvents(filtered);
  }, [events, activeLayers, activeSources, timeWindow, isPaused, replayCursor]);

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

  const hud = useMemo(() => {
    const now = timelineNow;
    let critical = 0;
    let active = 0;
    let muted = Math.max(0, events.length - filteredEvents.length);
    const byRegion = new Map();

    for (const e of filteredEvents) {
      if ((e?.severity || '').toLowerCase() === 'critical') critical += 1;
      const ageSec = Math.max(0, (now - eventTs(e)) / 1000);
      if (ageSec < 180) active += 1;
      if (e?.lat != null && e?.lon != null) {
        const key = formatGridRegion(e.lat, e.lon);
        byRegion.set(key, (byRegion.get(key) || 0) + 1);
      }
    }

    const topRegions = [...byRegion.entries()].sort((a, b) => b[1] - a[1]).slice(0, 3);
    return { critical, active, muted, topRegions };
  }, [events.length, filteredEvents, timelineNow]);

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
    if (event?.lat != null && event?.lon != null) {
      handleFlyTo(event.lat, event.lon, 1.1);
    }
    try {
      const rel = await getRelationships(event.id);
      setRelationships(rel);
    } catch (e) {
      setRelationships(null);
    }
  };

  const handleSearch = async (query) => {
    if (!query.trim()) {
      loadEvents();
      return;
    }
    try {
      const data = await searchEvents({ query, limit: 200 });
      setFilteredEvents(data.results || []);
    } catch (e) {
      console.error('Search failed:', e);
    }
  };

  const handleFlyTo = (lat, lon, duration = 1.5) => {
    if (viewerRef.current) {
      viewerRef.current.camera.flyTo({
        destination: Cesium.Cartesian3.fromDegrees(lon, lat, 550000),
        duration,
      });
    }
  };

  const toggleLayer = (type) => {
    setActiveLayers(prev => {
      if (prev.size === 1 && prev.has(type)) {
        return new Set(Object.keys(TYPE_COLORS_CSS));
      }
      return new Set([type]);
    });
  };

  return (
    <div style={{ width: '100%', height: '100%', position: 'relative', background: '#020617' }}>
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 1000,
        background: 'linear-gradient(180deg, rgba(2,6,23,0.98) 0%, rgba(2,6,23,0.5) 60%, rgba(2,6,23,0) 100%)',
        padding: '12px 20px', display: 'flex', alignItems: 'center', gap: 16,
        pointerEvents: 'none',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, pointerEvents: 'auto' }}>
          <span style={{ fontSize: 22 }}>🛰️</span>
          <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: 2, color: '#f472b6' }}>OSIRIS LIVE GRID</h1>
        </div>
        <div style={{ pointerEvents: 'auto', flex: 1, maxWidth: 450 }}>
          <SearchBar onSearch={handleSearch} />
        </div>
        <div style={{ pointerEvents: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
          {Object.keys(TIME_WINDOWS).map((k) => (
            <button
              key={k}
              onClick={() => setTimeWindow(k)}
              style={{
                border: '1px solid rgba(244,114,182,0.4)',
                background: timeWindow === k ? 'rgba(244,114,182,0.25)' : 'rgba(2,6,23,0.7)',
                color: timeWindow === k ? '#fdf2f8' : '#f9a8d4',
                borderRadius: 6,
                padding: '4px 8px',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              {k}
            </button>
          ))}
          <button
            onClick={() => {
              if (!isPaused) setReplayCursor(timelineBounds.max || Date.now());
              setIsPaused(p => !p);
            }}
            style={{
              border: '1px solid rgba(56,189,248,0.35)',
              background: isPaused ? 'rgba(56,189,248,0.25)' : 'rgba(2,6,23,0.7)',
              color: '#bae6fd', borderRadius: 6, padding: '4px 8px', fontSize: 11, cursor: 'pointer',
            }}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </button>
        </div>
        <div style={{ pointerEvents: 'auto' }}>
          <StatsBar stats={stats} />
        </div>
      </div>

      {isPaused && timelineBounds.min < timelineBounds.max && (
        <div style={{
          position: 'absolute',
          top: 56,
          left: '35%',
          width: '30%',
          zIndex: 1001,
          background: 'rgba(2,6,23,0.82)',
          border: '1px solid rgba(56,189,248,0.3)',
          borderRadius: 8,
          padding: '8px 10px',
          color: '#bae6fd',
          fontSize: 11,
        }}>
          <div style={{ marginBottom: 6 }}>Replay scrub</div>
          <input
            type="range"
            min={timelineBounds.min}
            max={timelineBounds.max}
            value={replayCursor || timelineBounds.max}
            onChange={(e) => setReplayCursor(Number(e.target.value))}
            style={{ width: '100%' }}
          />
        </div>
      )}

      <LayerPanel
        activeLayers={activeLayers}
        onToggle={toggleLayer}
        eventCounts={filteredEvents.reduce((acc, e) => {
          if (e && e.lat != null && e.lon != null) {
            acc[e.event_type] = (acc[e.event_type] || 0) + 1;
          }
          return acc;
        }, {})}
      />

      <div style={{
        position: 'absolute',
        top: 92,
        right: 16,
        zIndex: 999,
        width: 340,
        maxHeight: '60vh',
        overflow: 'auto',
        background: 'rgba(2,6,23,0.78)',
        border: '1px solid rgba(244,114,182,0.25)',
        borderRadius: 10,
        padding: 10,
        color: '#fbcfe8',
        pointerEvents: 'auto',
      }}>
        <div style={{ fontWeight: 700, marginBottom: 8, color: '#f472b6' }}>Live Event Feed</div>
        {feedRail.length === 0 && <div style={{ color: '#94a3b8' }}>Waiting for bursts…</div>}
        {feedRail.map(item => (
          <div
            key={item.id}
            onClick={() => item.event?.lat != null && item.event?.lon != null && handleEventClick(item.event)}
            style={{
              padding: '7px 6px',
              borderTop: '1px solid rgba(244,114,182,0.12)',
              cursor: item.event?.lat != null ? 'pointer' : 'default',
            }}
          >
            <div style={{ color: '#fdf2f8', fontSize: 12 }}>{item.label}</div>
            <div style={{ color: '#94a3b8', fontSize: 11 }}>
              {new Date(item.ts).toLocaleTimeString()} • {item.event?.severity || 'medium'}
            </div>
          </div>
        ))}
      </div>

      <div style={{
        position: 'absolute',
        bottom: 16,
        right: 16,
        zIndex: 999,
        background: 'rgba(2,6,23,0.85)',
        border: '1px solid rgba(56,189,248,0.3)',
        borderRadius: 8,
        padding: '10px 12px',
        fontSize: 12,
        color: '#cbd5f5',
        minWidth: 250,
        pointerEvents: 'auto',
      }}>
        <div style={{ fontWeight: 700, marginBottom: 6, color: '#67e8f9' }}>HUD</div>
        <div>Critical: <strong style={{ color: '#fb7185' }}>{hud.critical}</strong></div>
        <div>Active: <strong style={{ color: '#f59e0b' }}>{hud.active}</strong></div>
        <div>Muted: <strong style={{ color: '#a78bfa' }}>{hud.muted}</strong></div>
        <div>Top regions: {hud.topRegions.length ? hud.topRegions.map(([r, c]) => `${r} (${c})`).join(' • ') : '—'}</div>
        <div style={{ marginTop: 8, color: '#93c5fd' }}>Rendered events: {filteredEvents.length} | Geo: {geoStats.geoCount} | Non-geo: {geoStats.nonGeoCount}</div>
        <div>API: {apiLastFetchAt ? new Date(apiLastFetchAt).toLocaleTimeString() : '—'} ({apiEventCount}{apiError ? ' error' : ''})</div>
        <div>WS: {wsState} • {wsLastMessageAt ? new Date(wsLastMessageAt).toLocaleTimeString() : '—'} • {wsEventCount}</div>
        <div>3D tiles: {tilesetStatus} • tile errs: {tileErrors.length}</div>
        <div style={{ marginTop: 6 }}>
          <button
            onClick={() => setShowNonGeo(prev => !prev)}
            disabled={geoStats.nonGeoCount === 0}
            style={{
              background: 'rgba(56,189,248,0.12)',
              border: '1px solid rgba(56,189,248,0.28)',
              color: geoStats.nonGeoCount === 0 ? '#64748b' : '#67e8f9',
              padding: '4px 7px',
              borderRadius: 6,
              fontSize: 11,
              cursor: geoStats.nonGeoCount === 0 ? 'not-allowed' : 'pointer',
              opacity: geoStats.nonGeoCount === 0 ? 0.6 : 1,
            }}
          >
            {showNonGeo ? 'Hide' : 'Show'} non-geo ({geoStats.nonGeoCount})
          </button>
        </div>
      </div>

      {showNonGeo && geoStats.nonGeoCount > 0 && (
        <div style={{
          position: 'absolute',
          bottom: 16,
          left: 16,
          zIndex: 999,
          background: 'rgba(10,14,23,0.9)',
          border: '1px solid rgba(96,165,250,0.25)',
          borderRadius: 8,
          padding: '10px 12px',
          width: 460,
          maxHeight: 420,
          overflow: 'auto',
          fontSize: 12,
          color: '#cbd5f5',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 6, color: '#93c5fd' }}>Non-Geo Events</div>
          <div style={{ marginBottom: 6, color: '#94a3b8' }}>
            By type: {Object.entries(geoStats.nonGeoByType).map(([k, v]) => `${k} ${v}`).join(' • ')}
          </div>
          {filteredEvents.filter(e => e && (e.lat == null || e.lon == null)).slice(0, 60).map((e) => (
            <div
              key={e.id}
              style={{ padding: '6px 0', borderTop: '1px solid rgba(96,165,250,0.1)', cursor: 'pointer' }}
              onClick={() => handleEventClick(e)}
            >
              <div style={{ color: '#e2e8f0' }}>{e.title || 'Untitled'}</div>
              <div style={{ color: '#94a3b8' }}>{e.event_type} • {e.source}</div>
            </div>
          ))}
        </div>
      )}

      <div ref={cesiumContainerRef} style={{ width: '100%', height: '100%' }} />

      {selectedEvent && (
        <EntityDetail
          event={selectedEvent}
          relationships={relationships}
          onClose={() => { setSelectedEvent(null); setRelationships(null); setShowRelGraph(false); }}
          onShowGraph={() => setShowRelGraph(true)}
          onFlyTo={handleFlyTo}
        />
      )}

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
