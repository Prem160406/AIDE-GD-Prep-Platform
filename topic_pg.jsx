// src/features/student/topic_pg.jsx
import React, { useState, useEffect } from 'react';
import { getActiveTopics, runPipeline } from '../../services/api';

export default function TopicsPage() {
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    const fetchTopics = async () => {
      try {
        const data = await getActiveTopics();
        setTopics(data.topics || []);
      } catch (err) {
        setError('Failed to fetch discussion topics.');
      } finally {
        setLoading(false);
      }
    };
    fetchTopics();
  }, []);

  const handleRunPipeline = async () => {
    setRunning(true);
    setError(null);
    try {
      await runPipeline();
      const data = await getActiveTopics();
      setTopics(data.topics || []);
    } catch (err) {
      setError('Pipeline failed. Check backend logs.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '20px' }}>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h2 style={{ fontSize: '28px', color: '#333', margin: 0 }}>
          Discussion Topics
        </h2>
        <button
          onClick={handleRunPipeline}
          disabled={running}
          style={{
            padding: '10px 20px',
            background: running ? '#93c5fd' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '600',
            cursor: running ? 'not-allowed' : 'pointer',
            fontSize: '14px',
          }}
        >
          {running ? 'Generating...' : 'Generate New Topics'}
        </button>
      </div>

      {loading && <p>Loading topics...</p>}
      {error && <p style={{ color: '#dc2626' }}>{error}</p>}

      {!loading && !error && topics.length === 0 && (
        <p style={{ color: '#6b7280' }}>No topics available yet.</p>
      )}

      {!loading && !error && topics.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '20px',
          }}
        >
          {topics.map((topic) => (
            <div
              key={topic.id}
              style={{
                background: '#fff',
                padding: '20px',
                borderRadius: '10px',
                border: '1px solid #e5e7eb',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}
            >
              <h3 style={{ fontSize: '18px', marginBottom: '8px', color: '#111827' }}>
                {topic.title}
              </h3>

              <p style={{ fontSize: '14px', color: '#4b5563', marginBottom: '12px' }}>
                {topic.summary}
              </p>

              <p style={{ fontSize: '13px', color: '#6b7280' }}>
                <strong>Source:</strong>{' '}
                {topic.source_url
                  ? <a href={topic.source_url} target="_blank" rel="noreferrer" style={{ color: '#2563eb' }}>{topic.source}</a>
                  : topic.source}
              </p>

              {topic.date && (
                <p style={{ fontSize: '13px', color: '#6b7280' }}>
                  <strong>Date:</strong> {new Date(topic.date).toLocaleDateString()}
                </p>
              )}

              {topic.score != null && (
                <span
                  style={{
                    display: 'inline-block',
                    marginTop: '12px',
                    fontSize: '12px',
                    padding: '4px 8px',
                    background: '#d1fae5',
                    color: '#065f46',
                    borderRadius: '4px',
                    fontWeight: 'bold',
                  }}
                >
                  Score: {topic.score}/10
                </span>
              )}
            </div>
          ))}
        </div>
      )}

    </div>
  );
}