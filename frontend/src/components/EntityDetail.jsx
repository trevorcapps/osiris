import React from 'react';

const SEVERITY_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e',
};

export default function EntityDetail({ event, relationships, onClose, onShowGraph, onFlyTo }) {
  if (!event) return null;

  const relatedCount = relationships?.related?.length || 0;

  return (
    <div style={{
      position: 'absolute', top: 70, right: 12, zIndex: 1000,
      width: 360, maxHeight: 'calc(100vh - 100px)',
      background: 'rgba(15,23,42,0.95)', borderRadius: 12,
      border: '1px solid rgba(96,165,250,0.2)',
      backdropFilter: 'blur(10px)', overflowY: 'auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid rgba(96,165,250,0.1)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, textTransform: 'uppercase', color: '#64748b', marginBottom: 4 }}>
            {event.source} • {event.event_type}
          </div>
          <h3 style={{ fontSize: 14, fontWeight: 600, lineHeight: 1.4 }}>{event.title}</h3>
        </div>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#64748b',
          cursor: 'pointer', fontSize: 18, padding: 4,
        }}>✕</button>
      </div>

      {/* Body */}
      <div style={{ padding: '12px 16px' }}>
        {event.severity && (
          <span style={{
            display: 'inline-block', padding: '2px 8px', borderRadius: 4,
            fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
            background: SEVERITY_COLORS[event.severity] + '20',
            color: SEVERITY_COLORS[event.severity],
            marginBottom: 8,
          }}>{event.severity}</span>
        )}

        <p style={{ fontSize: 13, color: '#94a3b8', lineHeight: 1.5, marginBottom: 12 }}>
          {event.description}
        </p>

        {event.lat && event.lon && (
          <div style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>
            📍 {event.lat.toFixed(4)}, {event.lon.toFixed(4)}
            <button
              onClick={() => onFlyTo(event.lat, event.lon)}
              style={{
                marginLeft: 8, background: 'rgba(96,165,250,0.2)',
                border: 'none', color: '#60a5fa', borderRadius: 4,
                padding: '2px 6px', cursor: 'pointer', fontSize: 11,
              }}
            >Fly To</button>
          </div>
        )}

        <div style={{ fontSize: 11, color: '#64748b', marginBottom: 12 }}>
          🕐 {new Date(event.timestamp).toLocaleString()}
        </div>

        {event.url && (
          <a href={event.url} target="_blank" rel="noopener noreferrer" style={{
            display: 'block', fontSize: 12, color: '#60a5fa',
            marginBottom: 12, textDecoration: 'none',
          }}>🔗 Source →</a>
        )}

        {/* Entities */}
        {event.entities && event.entities.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 4 }}>
              Entities
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {event.entities.map((ent, i) => (
                <span key={i} style={{
                  padding: '2px 8px', borderRadius: 4, fontSize: 11,
                  background: 'rgba(96,165,250,0.15)', color: '#93c5fd',
                }}>{ent.name} <span style={{ color: '#64748b' }}>({ent.type})</span></span>
              ))}
            </div>
          </div>
        )}

        {/* Related Events */}
        {relatedCount > 0 && (
          <div>
            <div style={{
              fontSize: 11, color: '#64748b', fontWeight: 600, marginBottom: 4,
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span>Related Events ({relatedCount})</span>
              <button onClick={onShowGraph} style={{
                background: 'rgba(96,165,250,0.2)', border: 'none',
                color: '#60a5fa', borderRadius: 4, padding: '2px 8px',
                cursor: 'pointer', fontSize: 10,
              }}>🕸️ Graph View</button>
            </div>
            {relationships.related.slice(0, 8).map((rel, i) => (
              <div key={i} style={{
                padding: '6px 8px', borderRadius: 6, marginBottom: 4,
                background: 'rgba(30,41,59,0.8)', fontSize: 12,
              }}>
                <div style={{ fontWeight: 500 }}>{rel.title}</div>
                <div style={{ color: '#64748b', fontSize: 10 }}>
                  {rel.source} • Score: {(rel.score * 100).toFixed(0)}%
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Metadata */}
        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <details style={{ marginTop: 12 }}>
            <summary style={{ fontSize: 11, color: '#64748b', cursor: 'pointer' }}>
              Raw Metadata
            </summary>
            <pre style={{
              fontSize: 10, color: '#64748b', marginTop: 4,
              whiteSpace: 'pre-wrap', wordBreak: 'break-all',
            }}>{JSON.stringify(event.metadata, null, 2)}</pre>
          </details>
        )}
      </div>
    </div>
  );
}
