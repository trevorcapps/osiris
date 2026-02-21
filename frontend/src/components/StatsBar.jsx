import React from 'react';

export default function StatsBar({ stats }) {
  if (!stats) return null;
  return (
    <div style={{
      display: 'flex', gap: 16, fontSize: 12, color: '#94a3b8',
      marginLeft: 'auto', whiteSpace: 'nowrap',
    }}>
      <span>📡 <strong style={{ color: '#60a5fa' }}>{stats.active_feeds}</strong> feeds</span>
      <span>📊 <strong style={{ color: '#60a5fa' }}>{stats.total_events?.toLocaleString()}</strong> events</span>
      <span>🧠 <strong style={{ color: '#60a5fa' }}>{stats.vector_db_count?.toLocaleString()}</strong> vectors</span>
    </div>
  );
}
