import React, { useState } from 'react';

export default function SearchBar({ onSearch }) {
  const [query, setQuery] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} style={{ flex: 1, maxWidth: 500 }}>
      <input
        type="text"
        value={query}
        onChange={e => setQuery(e.target.value)}
        placeholder="Search events, entities, locations..."
        style={{
          width: '100%',
          padding: '8px 16px',
          borderRadius: 8,
          border: '1px solid rgba(96,165,250,0.3)',
          background: 'rgba(15,23,42,0.8)',
          color: '#e2e8f0',
          fontSize: 14,
          outline: 'none',
          backdropFilter: 'blur(10px)',
        }}
      />
    </form>
  );
}
