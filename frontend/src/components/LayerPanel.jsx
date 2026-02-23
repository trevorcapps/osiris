import React, { useState } from 'react';

const TYPE_LABELS = {
  conflict: '⚔️ Conflict',
  military: '🎖️ Military',
  aviation: '✈️ Aviation',
  maritime: '🚢 Maritime',
  earthquake: '🌍 Earthquake',
  weather: '🌩️ Weather',
  wildfire: '🔥 Wildfire',
  volcano: '🌋 Volcano',
  natural_disaster: '🌊 Natural Disaster',
  cyber: '💻 Cyber',
  infrastructure: '🏗️ Infrastructure',
  sanctions: '🚫 Sanctions',
  financial: '💰 Financial',
  news: '📰 News',
  humanitarian: '🤝 Humanitarian',
  health: '🏥 Health',
  terrorism: '💣 Terrorism',
};

const CSS_COLORS = {
  conflict: '#ef4444',
  military: '#8b0000',
  aviation: '#06b6d4',
  maritime: '#3b82f6',
  earthquake: '#f97316',
  weather: '#fde68a',
  wildfire: '#ff4500',
  volcano: '#8b0000',
  natural_disaster: '#ff8c00',
  cyber: '#22c55e',
  infrastructure: '#9370db',
  sanctions: '#eab308',
  financial: '#adff2f',
  news: '#ffffff',
  humanitarian: '#ff69b4',
  health: '#00fa9a',
  terrorism: '#ef4444',
};

export default function LayerPanel({ activeLayers, onToggle, eventCounts }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div style={{
      position: 'absolute', top: 70, left: 12, zIndex: 1000,
      background: 'rgba(15,23,42,0.9)', borderRadius: 12,
      border: '1px solid rgba(96,165,250,0.2)',
      backdropFilter: 'blur(10px)', width: collapsed ? 44 : 280,
      transition: 'width 0.2s', overflow: 'hidden',
    }}>
      <div
        onClick={() => setCollapsed(!collapsed)}
        style={{
          padding: '10px 12px', cursor: 'pointer', display: 'flex',
          alignItems: 'center', justifyContent: 'space-between',
          borderBottom: collapsed ? 'none' : '1px solid rgba(96,165,250,0.1)',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: '#60a5fa' }}>
          {collapsed ? '📊' : '📊 Layers'}
        </span>
        {!collapsed && <span style={{ fontSize: 11, color: '#64748b' }}>{collapsed ? '' : '◀'}</span>}
      </div>
      {!collapsed && (
        <div style={{ padding: '4px 8px 8px', maxHeight: 'calc(100vh - 160px)', overflowY: 'auto' }}>
          {Object.entries(TYPE_LABELS).map(([type, label]) => (
            <div
              key={type}
              onClick={() => onToggle(type)}
              style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '4px 6px', cursor: 'pointer', borderRadius: 6,
                opacity: activeLayers.has(type) ? 1 : 0.4,
                fontSize: 12,
              }}
            >
              <div style={{
                width: 10, height: 10, borderRadius: '50%',
                background: CSS_COLORS[type], flexShrink: 0,
              }} />
              <span style={{ flex: 1 }}>{label}</span>
              <span style={{ color: '#64748b', fontSize: 10 }}>
                {eventCounts[type] || 0}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
