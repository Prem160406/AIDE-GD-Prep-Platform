import React, { useState, useEffect } from 'react';
import { supabase } from '../../supabase';
import { getActiveTopics, runPipeline } from '../../services/api';

export default function StudentDashboard({ session }) {
  const [topics, setTopics] = useState([]);
  const [practiced, setPracticed] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetchTopics();
    fetchPracticed();
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

  const fetchPracticed = async () => {
    const { data } = await supabase
      .from('practiced_topics')
      .select('topic_id')
      .eq('user_id', session.user.id);
    if (data) setPracticed(new Set(data.map(r => r.topic_id)));
  };

  const togglePracticed = async (topicId) => {
    if (practiced.has(topicId)) {
      await supabase.from('practiced_topics')
        .delete()
        .eq('user_id', session.user.id)
        .eq('topic_id', topicId);
      setPracticed(prev => { const s = new Set(prev); s.delete(topicId); return s; });
    } else {
      await supabase.from('practiced_topics')
        .insert({ user_id: session.user.id, topic_id: topicId });
      setPracticed(prev => new Set([...prev, topicId]));
    }
  };

  const handleRunPipeline = async () => {
    setRunning(true);
    setError(null);
    try {
      await runPipeline();
      await fetchTopics();
    } catch {
      setError('Pipeline failed. Check backend logs.');
    } finally {
      setRunning(false);
    }
  };

  const handleLogout = () => supabase.auth.signOut();

  const filteredTopics = topics.filter(t =>
    t.title?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ minHeight: '100vh', background: '#f9fafb' }}>

      {/* Navbar */}
      <nav style={{ background: '#fff', borderBottom: '1px solid #e5e7eb', padding: '0 32px', height: '64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span style={{ fontSize: '20px', fontWeight: '800', color: '#0f766e' }}>AIDE</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span style={{ fontSize: '14px', color: '#6b7280' }}>
            {session.user.user_metadata?.full_name || session.user.email}
          </span>
          <button onClick={handleLogout} style={{ padding: '8px 16px', background: '#f3f4f6', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '13px', fontWeight: '600', color: '#374151' }}>
            Logout
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ background: 'linear-gradient(135deg, #0f766e 0%, #0e7490 100%)', padding: '48px 32px', color: '#fff' }}>
        <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.15)', padding: '6px 14px', borderRadius: '20px', fontSize: '13px', marginBottom: '16px' }}>
            ✦ AI-Powered · Live News Integration
          </div>
          <h1 style={{ fontSize: '36px', fontWeight: '800', margin: '0 0 12px 0' }}>AIDE — Automated Intelligent Discussion Engine</h1>
          <p style={{ fontSize: '16px', opacity: 0.85, maxWidth: '560px', margin: '0 0 24px 0', lineHeight: 1.6 }}>
            Transforms breaking news into structured Group Discussion topic cards — so you're always placement-ready.
          </p>
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '14px', opacity: 0.8 }}>
              {practiced.size} topic{practiced.size !== 1 ? 's' : ''} practiced
            </span>
            <button onClick={handleRunPipeline} disabled={running} style={{
              padding: '10px 24px', background: running ? 'rgba(255,255,255,0.3)' : '#fff',
              color: running ? '#fff' : '#0f766e', border: 'none', borderRadius: '8px',
              fontWeight: '700', fontSize: '14px', cursor: running ? 'not-allowed' : 'pointer',
            }}>
              {running ? 'Generating...' : '⚡ Generate New Topics'}
            </button>
          </div>
        </div>
      </div>

      {/* Search */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '32px 32px 0' }}>
        <div style={{ display: 'flex', alignItems: 'center', background: '#fff', border: '1px solid #e5e7eb', borderRadius: '10px', padding: '10px 16px', gap: '8px', marginBottom: '24px' }}>
          <span style={{ color: '#9ca3af' }}>🔍</span>
          <input
            placeholder="Search GD topics..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ border: 'none', outline: 'none', fontSize: '14px', width: '100%', color: '#111827' }}
          />
        </div>

        {error && <p style={{ color: '#dc2626', marginBottom: '16px' }}>{error}</p>}
        {loading && <p style={{ color: '#6b7280' }}>Loading topics...</p>}

        {!loading && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '20px', paddingBottom: '40px' }}>
            {filteredTopics.map(topic => (
              <TopicCard
                key={topic.id}
                topic={topic}
                practiced={practiced.has(topic.id)}
                onTogglePracticed={() => togglePracticed(topic.id)}
              />
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

function TopicCard({ topic, practiced, onTogglePracticed }) {
  return (
    <div style={{ background: '#fff', borderRadius: '12px', border: '1px solid #e5e7eb', padding: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.07)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <h3 style={{ fontSize: '17px', fontWeight: '700', color: '#111827', margin: 0, lineHeight: 1.4 }}>
        {topic.title}
      </h3>

      <p style={{ fontSize: '14px', color: '#4b5563', margin: 0, lineHeight: 1.6 }}>
        {topic.summary}
      </p>

      <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#6b7280', flexWrap: 'wrap' }}>
        {topic.date && <span>📅 {new Date(topic.date).toLocaleDateString()}</span>}
        {topic.source && (
          <span>
            📰{' '}
            {topic.source_url
              ? <a href={topic.source_url} target="_blank" rel="noreferrer" style={{ color: '#0f766e' }}>{topic.source}</a>
              : topic.source}
          </span>
        )}
        {topic.score != null && <span>⭐ {topic.score}/10</span>}
      </div>

      <button onClick={onTogglePracticed} style={{
        marginTop: '4px', padding: '10px', borderRadius: '8px', border: 'none',
        background: practiced ? '#dcfce7' : '#0f766e',
        color: practiced ? '#166534' : '#fff',
        fontWeight: '600', fontSize: '13px', cursor: 'pointer',
      }}>
        {practiced ? '✓ Practiced' : '▶ Mark as Practiced'}
      </button>
    </div>
  );
}