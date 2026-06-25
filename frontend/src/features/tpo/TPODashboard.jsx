import React, { useState, useEffect } from 'react';
import { supabase } from '../../supabase';
import { getActiveTopics } from '../../services/api';

export default function TPODashboard({ session }) {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [error, setError] = useState(null);

  const filters = ['All', 'Controversy', 'Policy', 'Ethics', 'Multi-Stakeholder'];

  useEffect(() => {
    fetchTopics();
  }, []);

  const fetchTopics = async () => {
    try {
      const data = await getActiveTopics();
      setTopics(data.topics || []);
    } catch {
      setError('Failed to load topics.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => supabase.auth.signOut();

  const handleExport = () => {
    const rows = [
      ['Title', 'Summary', 'Source', 'Date', 'Score', 'Controversy', 'Policy', 'Ethics', 'Multi-Stakeholder', 'Pipeline Version'],
      ...topics.map(t => [
        t.title,
        t.summary,
        t.source,
        t.date,
        t.score,
        t.controversy ? 'Yes' : 'No',
        t.policy_relevance ? 'Yes' : 'No',
        t.ethical_dimension ? 'Yes' : 'No',
        t.multiple_stakeholders ? 'Yes' : 'No',
        t.pipeline_version || '',
      ])
    ];

    const csv = rows.map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AIDE_Topics_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const filteredTopics = topics.filter(t => {
    const matchSearch = t.title?.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === 'All' ? true :
      filter === 'Controversy' ? t.controversy :
      filter === 'Policy' ? t.policy_relevance :
      filter === 'Ethics' ? t.ethical_dimension :
      filter === 'Multi-Stakeholder' ? t.multiple_stakeholders : true;
    return matchSearch && matchFilter;
  });

  return (
    <div style={{ minHeight: '100vh', background: '#f9fafb' }}>

      {/* Navbar */}
      <nav style={{ background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '0 32px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '20px', fontWeight: '800', color: '#0f766e' }}>AIDE</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>
            {session.user.user_metadata?.full_name || session.user.email}
          </span>
          <button onClick={handleExport} style={{ padding: '8px 16px', background: '#0f766e', color: '#fff', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: '600' }}>
            ⬇ Export CSV
          </button>
          <button onClick={handleLogout} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: '600', color: '#374151' }}>
            Logout
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ background: 'linear-gradient(135deg, #0f766e 0%, #0e7490 100%)', padding: '48px 32px', color: '#fff' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <h1 style={{ fontSize: '36px', fontWeight: '800', margin: '0 0 12px 0' }}>TPO Dashboard</h1>
          <p style={{ fontSize: '16px', opacity: 0.85, maxWidth: '560px', margin: 0, lineHeight: 1.6 }}>
            Browse AI-generated GD topics. Export the full list for faculty or placement reports.
          </p>
          <p style={{ fontSize: '14px', opacity: 0.75, marginTop: '12px' }}>
            {topics.length} topics available · Last updated {topics[0]?.date ? new Date(topics[0].date).toLocaleDateString() : '—'}
          </p>
        </div>
      </div>

      {/* Search + Filters */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 32px 0' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap' }}>
          <div style={{ flex: 1, minWidth: '240px', display: 'flex', alignItems: 'center', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 16px', gap: '8px' }}>
            <span style={{ color: '#9ca3af' }}>🔍</span>
            <input
              placeholder="Search topics..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ border: 'none', outline: 'none', fontSize: '14px', width: '100%' }}
            />
          </div>
          {filters.map(f => (
            <button key={f} onClick={() => setFilter(f)} style={{
              padding: '8px 16px', borderRadius: '20px', border: '1px solid',
              borderColor: filter === f ? '#0f766e' : '#e5e7eb',
              background: filter === f ? '#0f766e' : '#fff',
              color: filter === f ? '#fff' : '#4b5563',
              fontWeight: '500', fontSize: '13px', cursor: 'pointer',
            }}>
              {f}
            </button>
          ))}
        </div>

        {error && <p style={{ color: '#dc2626' }}>{error}</p>}
        {loading && <p style={{ color: '#6b7280' }}>Loading topics...</p>}

        {!loading && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px', paddingBottom: '40px' }}>
            {filteredTopics.map(topic => (
              <TPOTopicCard key={topic.id} topic={topic} />
            ))}
            {filteredTopics.length === 0 && (
              <p style={{ color: '#6b7280', gridColumn: '1/-1' }}>No topics match your search.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function TPOTopicCard({ topic }) {
  const tags = [
    topic.controversy && { label: 'Controversy', color: '#fef3c7', text: '#92400e' },
    topic.policy_relevance && { label: 'Policy', color: '#dbeafe', text: '#1e40af' },
    topic.ethical_dimension && { label: 'Ethics', color: '#f3e8ff', text: '#6b21a8' },
    topic.multiple_stakeholders && { label: 'Multi-Stakeholder', color: '#dcfce7', text: '#166534' },
  ].filter(Boolean);

  return (
    <div style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e5e7eb', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.07)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {tags.length > 0 && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {tags.map(tag => (
            <span key={tag.label} style={{ padding: '3px 10px', borderRadius: '12px', fontSize: '12px', fontWeight: '600', background: tag.color, color: tag.text }}>
              {tag.label}
            </span>
          ))}
        </div>
      )}

      <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#111827', margin: 0, lineHeight: 1.4 }}>
        {topic.title}
      </h3>

      <p style={{ fontSize: '14px', color: '#4b5563', margin: 0, lineHeight: 1.6 }}>
        {topic.summary}
      </p>

      <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#6b7280', flexWrap: 'wrap' }}>
        {topic.date && <span>📅 {new Date(topic.date).toLocaleDateString()}</span>}
        {topic.source && (
          <span>📰{' '}
            {topic.source_url
              ? <a href={topic.source_url} target="_blank" rel="noreferrer" style={{ color: '#0f766e' }}>{topic.source}</a>
              : topic.source}
          </span>
        )}
        {topic.score != null && <span>⭐ {topic.score}/10</span>}
        {topic.pipeline_version && <span>🔧 v{topic.pipeline_version}</span>}
        {topic.factual_freshness && <span>🕐 {topic.factual_freshness}</span>}
      </div>
    </div>
  );
}