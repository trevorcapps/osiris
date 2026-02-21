import React, { useEffect, useRef } from 'react';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';

const SOURCE_COLORS = {
  gdelt: '#ffffff', acled: '#ef4444', usgs: '#f97316', opensky: '#06b6d4',
  noaa: '#fde68a', nasa_eonet: '#22c55e', nasa_firms: '#ff4500',
  cisa_kev: '#22c55e', ofac: '#eab308', greynoise: '#22c55e',
  shodan: '#adff2f', rss_news: '#ffffff', reddit: '#ff4500',
  who: '#00fa9a', submarine_cables: '#9370db', ioda: '#9370db',
};

export default function RelationshipGraph({ event, relationships, onClose, onSelectEvent }) {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!containerRef.current || !event || !relationships?.related) return;

    const nodes = new DataSet();
    const edges = new DataSet();

    // Center node
    nodes.add({
      id: event.id,
      label: event.title?.substring(0, 40) + (event.title?.length > 40 ? '...' : ''),
      color: { background: '#60a5fa', border: '#3b82f6' },
      font: { color: '#e2e8f0', size: 12 },
      size: 25,
    });

    // Related nodes
    relationships.related.forEach((rel, i) => {
      const color = SOURCE_COLORS[rel.source] || '#64748b';
      nodes.add({
        id: rel.id || `rel-${i}`,
        label: (rel.title || 'Unknown')?.substring(0, 35) + ((rel.title || '').length > 35 ? '...' : ''),
        color: { background: color + '40', border: color },
        font: { color: '#94a3b8', size: 10 },
        size: 10 + (rel.score || 0) * 15,
        title: `${rel.source} | Score: ${((rel.score || 0) * 100).toFixed(0)}%\n${rel.description || ''}`,
      });
      edges.add({
        from: event.id,
        to: rel.id || `rel-${i}`,
        width: 1 + (rel.score || 0) * 3,
        color: { color: color + '60' },
        label: `${((rel.score || 0) * 100).toFixed(0)}%`,
        font: { size: 8, color: '#64748b' },
      });
    });

    const network = new Network(containerRef.current, { nodes, edges }, {
      physics: { solver: 'forceAtlas2Based', stabilization: { iterations: 50 } },
      nodes: { shape: 'dot', borderWidth: 2 },
      edges: { smooth: { type: 'continuous' } },
      interaction: { hover: true, tooltipDelay: 200 },
      layout: { improvedLayout: true },
    });

    network.on('click', (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const rel = relationships.related.find(r => r.id === nodeId);
        if (rel) onSelectEvent(rel);
      }
    });

    return () => network.destroy();
  }, [event, relationships]);

  return (
    <div style={{
      position: 'absolute', bottom: 20, left: '50%', transform: 'translateX(-50%)',
      zIndex: 1000, width: 700, height: 400,
      background: 'rgba(15,23,42,0.95)', borderRadius: 12,
      border: '1px solid rgba(96,165,250,0.2)',
      backdropFilter: 'blur(10px)', overflow: 'hidden',
    }}>
      <div style={{
        padding: '8px 16px', borderBottom: '1px solid rgba(96,165,250,0.1)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#60a5fa' }}>
          🕸️ Relationship Graph — {relationships?.related?.length || 0} connections
        </span>
        <button onClick={onClose} style={{
          background: 'none', border: 'none', color: '#64748b',
          cursor: 'pointer', fontSize: 16,
        }}>✕</button>
      </div>
      <div ref={containerRef} style={{ width: '100%', height: 'calc(100% - 40px)' }} />
    </div>
  );
}
