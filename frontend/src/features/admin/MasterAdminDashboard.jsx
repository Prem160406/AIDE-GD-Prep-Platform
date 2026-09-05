import React, { useState, useEffect } from 'react';
import { supabase } from '../../supabase';

function formatScore(val) {
  if (val == null) return null;
  const num = Number(val);
  if (isNaN(num)) return null;
  if (num <= 1.0) return Math.round(num * 100);
  if (num <= 10.0) return Math.round(num * 10);
  return Math.round(num);
}

function getCategoryTag(topic) {
  const text = ((topic.title || '') + ' ' + (topic.summary || '')).toLowerCase();
  if (text.includes('ai') || text.includes('tech') || text.includes('digital') || text.includes('cyber') || text.includes('data') || text.includes('model')) {
    return '⚡ TECH & INNOVATION';
  }
  if (text.includes('econ') || text.includes('esg') || text.includes('bank') || text.includes('fiscal') || text.includes('market') || text.includes('trade') || text.includes('poverty') || text.includes('income')) {
    return '📊 ECONOMICS & BUSINESS';
  }
  if (text.includes('policy') || text.includes('gov') || text.includes('parliament') || text.includes('india') || text.includes('state') || text.includes('law') || text.includes('court')) {
    return '🏛️ POLICY & GOVERNANCE';
  }
  if (text.includes('ethic') || text.includes('social') || text.includes('privacy') || text.includes('climate') || text.includes('rights')) {
    return '⚖️ ETHICS & SOCIETY';
  }
  if (text.includes('world') || text.includes('global') || text.includes('foreign') || text.includes('us') || text.includes('china') || text.includes('war')) {
    return '🌐 GLOBAL AFFAIRS';
  }
  return '📰 NATIONAL DISPATCH';
}

function getTierBadge(scoreVal) {
  const score = formatScore(scoreVal);
  if (score == null) return null;
  if (score >= 80) return { label: 'DISTINCTION', color: '#15803d', bg: '#dcfce7' };
  if (score >= 60) return { label: 'MERIT', color: '#b45309', bg: '#fef3c7' };
  if (score >= 40) return { label: 'PASS', color: '#1d4ed8', bg: '#dbeafe' };
  return { label: 'LOW', color: '#b91c1c', bg: '#fee2e2' };
}

export default function MasterAdminDashboard({ session, profile }) {
  const [topics, setTopics] = useState([]);
  const [runs, setRuns] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [systemStatus, setSystemStatus] = useState({ is_live: true, message: '' });
  const [loading, setLoading] = useState(true);
  const [triggering, setTriggering] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');

  useEffect(() => {
    fetchInitialData();

    // Subscribe to system_status changes
    const statusSub = supabase
      .channel('public:system_status')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'system_status' }, (payload) => {
        if (payload.new) setSystemStatus(payload.new);
      })
      .subscribe();

    // Subscribe to pipeline_jobs changes
    const jobsSub = supabase
      .channel('public:pipeline_jobs')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'pipeline_jobs' }, () => {
        fetchJobs();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(statusSub);
      supabase.removeChannel(jobsSub);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    await Promise.all([fetchSystemStatus(), fetchTopics(), fetchRuns(), fetchJobs()]);
    setLoading(false);
  };

  const fetchSystemStatus = async () => {
    const { data } = await supabase.from('system_status').select('*').eq('id', 1).single();
    if (data) setSystemStatus(data);
  };

  const fetchTopics = async () => {
    const { data } = await supabase
      .from('topics')
      .select('*')
      .order('created_at', { ascending: false });
    if (data) setTopics(data);
  };

  const fetchRuns = async () => {
    const { data } = await supabase
      .from('pipeline_runs')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(15);
    if (data) setRuns(data);
  };

  const fetchJobs = async () => {
    const { data } = await supabase
      .from('pipeline_jobs')
      .select('*')
      .order('created_at', { ascending: false })
      .limit(10);
    if (data) setJobs(data);
  };

  const handleToggleSystemStatus = async () => {
    const nextLiveState = !systemStatus.is_live;
    const nextMessage = nextLiveState
      ? 'System is operational.'
      : 'System is currently down for scheduled maintenance.';

    const { error } = await supabase
      .from('system_status')
      .update({ is_live: nextLiveState, message: nextMessage, updated_at: new Date().toISOString() })
      .eq('id', 1);

    if (error) {
      setStatusMessage({ type: 'error', text: 'Failed to update system status: ' + error.message });
    } else {
      setSystemStatus(prev => ({ ...prev, is_live: nextLiveState, message: nextMessage }));
      setStatusMessage({ type: 'success', text: `System ${nextLiveState ? 'enabled (Live Operational)' : 'disabled (Maintenance Mode)'}.` });
    }
  };

  const handleTriggerPipeline = async () => {
    setTriggering(true);
    setStatusMessage(null);

    const { error } = await supabase.from('pipeline_jobs').insert({
      status: 'pending',
      triggered_by: session.user.id,
    });

    if (error) {
      setStatusMessage({ type: 'error', text: 'Failed to queue pipeline run: ' + error.message });
    } else {
      setStatusMessage({ type: 'success', text: 'Pipeline run queued successfully! Python worker will ingest & score topics.' });
      await fetchJobs();
    }
    setTriggering(false);
  };

  const handleLogout = () => supabase.auth.signOut();

  const filteredTopics = topics.filter(t => {
    const matchSearch = t.title?.toLowerCase().includes(search.toLowerCase()) ||
      t.summary?.toLowerCase().includes(search.toLowerCase()) ||
      (t.source_name || t.source || '').toLowerCase().includes(search.toLowerCase());
    const matchFilter = statusFilter === 'All' ? true :
      (statusFilter === 'Active' || statusFilter === 'Published') ? (t.status === 'active' || t.status === 'published') :
      t.status === statusFilter.toLowerCase();
    return matchSearch && matchFilter;
  });

  const currentDateStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  }).toUpperCase();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f4efe6', color: '#292524', fontFamily: "'Georgia', serif", padding: '24px' }}>
      <div style={{ maxWidth: '1280px', margin: '0 auto' }}>

        {/* TOP MASTHEAD */}
        <header style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          alignItems: 'center', gap: '16px', padding: '16px 0',
          borderTop: '3px double #292524', borderBottom: '3px double #292524', marginBottom: '16px'
        }}>
          {/* Left Metadata */}
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#44403c',
            border: '1px solid #a8a29e', padding: '10px', backgroundColor: '#eae3d6'
          }}>
            <div style={{ fontWeight: '700' }}>VOL. I · NO. {topics.length || 143}</div>
            <div style={{ color: '#57534e', marginTop: '2px' }}>{currentDateStr}</div>
            <div style={{ color: '#78716c', marginTop: '2px', fontSize: '10px' }}>EDITION: MASTER CONTROL</div>
          </div>

          {/* Center Brand Title */}
          <div style={{ textAlign: 'center' }}>
            <h1 style={{
              fontFamily: "'Playfair Display', serif", fontSize: 'clamp(2.2rem, 5vw, 3.8rem)',
              fontWeight: '900', letterSpacing: '-0.02em', textTransform: 'uppercase',
              margin: 0, lineHeight: 1
            }}>
              The AIDE Daily
            </h1>
            <div style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: '11px',
              letterSpacing: '0.15em', textTransform: 'uppercase', color: '#57534e', marginTop: '6px'
            }}>
              § MASTER CONTROL · SYSTEM COMMAND & OVERVIEW
            </div>
          </div>

          {/* Right User Bar */}
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px',
            fontFamily: "'JetBrains Mono', monospace", fontSize: '12px'
          }}>
            <div style={{
              display: 'inline-block', backgroundColor: '#292524', color: '#f4efe6',
              padding: '2px 8px', fontSize: '10px', fontWeight: '700', letterSpacing: '0.05em'
            }}>
              OPERATOR: {profile?.role?.toUpperCase() || 'MASTER ADMIN'}
            </div>
            <span style={{ fontWeight: '600', color: '#44403c' }}>{profile?.full_name || session.user.email}</span>
            <button
              onClick={handleLogout}
              style={{
                fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '700',
                backgroundColor: 'transparent', border: '1px solid #292524', padding: '4px 10px',
                cursor: 'pointer', color: '#292524', textTransform: 'uppercase', marginTop: '2px'
              }}
            >
              [ LOGOUT ]
            </button>
          </div>
        </header>

        {/* SUB-HEADER DISPATCH NAV / CONTROL BAR */}
        <div style={{
          borderBottom: '1px solid #292524', paddingBottom: '12px', marginBottom: '24px',
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px',
          fontFamily: "'JetBrains Mono', monospace", fontSize: '12px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontWeight: '700' }}>
            <span style={{ backgroundColor: '#292524', color: '#f4efe6', padding: '2px 6px' }}>§ COMMAND</span>
            <span>SYSTEM STATE: {systemStatus.is_live ? 'ONLINE' : 'MAINTENANCE'}</span>
            <span>QUEUED JOBS: {jobs.filter(j => j.status === 'pending' || j.status === 'running').length}</span>
            <span>TOTAL TOPICS: {topics.length}</span>
          </div>
        </div>

        {/* STATUS NOTIFICATION ALERT */}
        {statusMessage && (
          <div style={{
            border: `2px solid ${statusMessage.type === 'error' ? '#991b1b' : '#166534'}`,
            backgroundColor: statusMessage.type === 'error' ? '#fee2e2' : '#dcfce7',
            color: statusMessage.type === 'error' ? '#991b1b' : '#166534',
            padding: '12px 16px', marginBottom: '24px',
            fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', fontWeight: '700'
          }}>
            {statusMessage.type === 'error' ? '✖ [ ERROR ] ' : '✓ [ SUCCESS ] '}
            {statusMessage.text}
          </div>
        )}

        {/* EXECUTIVE CONTROL STATIONS (2-COLUMN GRID) */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px', marginBottom: '32px' }}>
          
          {/* CONTROL STATION 1: SYSTEM AVAILABILITY & LOCKOUT */}
          <section style={{
            border: '2px solid #292524', backgroundColor: '#eae3d6', padding: '20px',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
          }}>
            <div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                borderBottom: '1px solid #a8a29e', paddingBottom: '8px', marginBottom: '12px'
              }}>
                <h3 style={{
                  fontFamily: "'Playfair Display', serif", fontSize: '18px', fontWeight: '700',
                  margin: 0, textTransform: 'uppercase'
                }}>
                  I. System Lockout & Maintenance
                </h3>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800',
                  padding: '2px 8px', border: '1px solid',
                  borderColor: systemStatus.is_live ? '#166534' : '#991b1b',
                  color: systemStatus.is_live ? '#166534' : '#991b1b',
                  backgroundColor: systemStatus.is_live ? '#dcfce7' : '#fee2e2'
                }}>
                  {systemStatus.is_live ? '[ LIVE OPERATIONAL ]' : '[ MAINTENANCE MODE ]'}
                </span>
              </div>
              <p style={{ fontSize: '13px', color: '#44403c', marginBottom: '16px', lineHeight: '1.4' }}>
                {systemStatus.message || 'No system announcement message currently set.'}
              </p>
            </div>
            <button
              onClick={handleToggleSystemStatus}
              style={{
                fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', fontWeight: '800',
                padding: '10px 16px', cursor: 'pointer', textTransform: 'uppercase',
                border: '2px solid #292524',
                backgroundColor: systemStatus.is_live ? '#991b1b' : '#166534',
                color: '#ffffff', transition: 'all 0.15s ease'
              }}
            >
              {systemStatus.is_live ? '🔒 [ ENGAGE MAINTENANCE LOCKOUT ]' : '🔓 [ RESTORE LIVE OPERATIONS ]'}
            </button>
          </section>

          {/* CONTROL STATION 2: INGESTION PIPELINE TRIGGER */}
          <section style={{
            border: '2px solid #292524', backgroundColor: '#eae3d6', padding: '20px',
            display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
          }}>
            <div>
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                borderBottom: '1px solid #a8a29e', paddingBottom: '8px', marginBottom: '12px'
              }}>
                <h3 style={{
                  fontFamily: "'Playfair Display', serif", fontSize: '18px', fontWeight: '700',
                  margin: 0, textTransform: 'uppercase'
                }}>
                  II. Ingestion & Scoring Engine
                </h3>
                <span style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '700', color: '#57534e'
                }}>
                  ON-DEMAND TRIGGER
                </span>
              </div>
              <p style={{ fontSize: '13px', color: '#44403c', marginBottom: '16px', lineHeight: '1.4' }}>
                Dispatches an asynchronous pipeline job into Supabase. The background Python worker ingests RSS feeds, evaluates candidates across 8 criteria, and inserts qualified dispatches.
              </p>
            </div>
            <button
              onClick={handleTriggerPipeline}
              disabled={triggering}
              style={{
                fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', fontWeight: '800',
                padding: '10px 16px', cursor: triggering ? 'not-allowed' : 'pointer', textTransform: 'uppercase',
                border: '2px solid #292524',
                backgroundColor: triggering ? '#78716c' : '#292524',
                color: '#f4efe6', transition: 'all 0.15s ease'
              }}
            >
              {triggering ? '⚡ [ QUEUING PIPELINE... ]' : '⚡ [ RUN INGESTION & SCORING PIPELINE NOW ]'}
            </button>
          </section>

        </div>

        {/* SECTION 1: PIPELINE JOBS QUEUE */}
        <section style={{ border: '2px solid #292524', padding: '20px', backgroundColor: '#eae3d6', marginBottom: '32px' }}>
          <div style={{ borderBottom: '2px solid #292524', paddingBottom: '8px', marginBottom: '16px' }}>
            <h2 style={{
              fontFamily: "'Playfair Display', serif", fontSize: '20px', fontWeight: '800',
              textTransform: 'uppercase', margin: 0
            }}>
              § PIPELINE EXECUTION QUEUE (JOB QUEUE)
            </h2>
          </div>
          {jobs.length === 0 ? (
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: '#57534e', fontStyle: 'italic' }}>
              No pipeline trigger jobs recorded.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #292524', textTransform: 'uppercase', color: '#44403c' }}>
                    <th style={{ padding: '8px' }}>JOB ID</th>
                    <th style={{ padding: '8px' }}>STATUS</th>
                    <th style={{ padding: '8px' }}>QUEUED AT</th>
                    <th style={{ padding: '8px' }}>COMPLETED AT</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(job => (
                    <tr key={job.id} style={{ borderBottom: '1px solid #a8a29e' }}>
                      <td style={{ padding: '8px', fontWeight: '700' }}>#{job.id}</td>
                      <td style={{ padding: '8px' }}>
                        <span style={{
                          padding: '2px 6px', fontWeight: '800', border: '1px solid',
                          borderColor: job.status === 'completed' ? '#166534' : job.status === 'pending' ? '#b45309' : job.status === 'running' ? '#1d4ed8' : '#991b1b',
                          color: job.status === 'completed' ? '#166534' : job.status === 'pending' ? '#b45309' : job.status === 'running' ? '#1d4ed8' : '#991b1b',
                          backgroundColor: job.status === 'completed' ? '#dcfce7' : job.status === 'pending' ? '#fef3c7' : job.status === 'running' ? '#dbeafe' : '#fee2e2'
                        }}>
                          [{job.status.toUpperCase()}]
                        </span>
                      </td>
                      <td style={{ padding: '8px', color: '#57534e' }}>{new Date(job.created_at).toLocaleString()}</td>
                      <td style={{ padding: '8px', color: '#57534e' }}>{job.completed_at ? new Date(job.completed_at).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SECTION 2: TELEMETRY & OBSERVABILITY LOGS */}
        <section style={{ border: '2px solid #292524', padding: '20px', backgroundColor: '#eae3d6', marginBottom: '32px' }}>
          <div style={{ borderBottom: '2px solid #292524', paddingBottom: '8px', marginBottom: '16px' }}>
            <h2 style={{
              fontFamily: "'Playfair Display', serif", fontSize: '20px', fontWeight: '800',
              textTransform: 'uppercase', margin: 0
            }}>
              § SYSTEM TELEMETRY & PIPELINE RUN LOGS
            </h2>
          </div>
          {runs.length === 0 ? (
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: '#57534e', fontStyle: 'italic' }}>
              No pipeline run telemetry recorded yet.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid #292524', textTransform: 'uppercase', color: '#44403c' }}>
                    <th style={{ padding: '8px' }}>TIMESTAMP</th>
                    <th style={{ padding: '8px' }}>RAW RSS</th>
                    <th style={{ padding: '8px' }}>FETCHED</th>
                    <th style={{ padding: '8px' }}>SCORED</th>
                    <th style={{ padding: '8px' }}>FINAL ACCEPTED</th>
                    <th style={{ padding: '8px' }}>FAILED</th>
                    <th style={{ padding: '8px' }}>DURATION</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map(run => (
                    <tr key={run.id} style={{ borderBottom: '1px solid #a8a29e' }}>
                      <td style={{ padding: '8px', fontWeight: '700' }}>{new Date(run.created_at).toLocaleString()}</td>
                      <td style={{ padding: '8px' }}>{run.raw_count}</td>
                      <td style={{ padding: '8px' }}>{run.fetched_count}</td>
                      <td style={{ padding: '8px' }}>{run.scored_count}</td>
                      <td style={{ padding: '8px', color: '#15803d', fontWeight: '800' }}>{run.final_count}</td>
                      <td style={{ padding: '8px', color: run.failed_count > 0 ? '#b91c1c' : '#57534e', fontWeight: run.failed_count > 0 ? '700' : '400' }}>{run.failed_count}</td>
                      <td style={{ padding: '8px' }}>{run.duration_seconds ? `${run.duration_seconds}s` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* SECTION 3: MASTER TOPIC DIRECTORY & INVENTORY */}
        <section style={{ border: '2px solid #292524', padding: '20px', backgroundColor: '#eae3d6' }}>
          <div style={{
            display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center',
            borderBottom: '2px solid #292524', paddingBottom: '12px', marginBottom: '16px', gap: '12px'
          }}>
            <h2 style={{
              fontFamily: "'Playfair Display', serif", fontSize: '20px', fontWeight: '800',
              textTransform: 'uppercase', margin: 0
            }}>
              § MASTER TOPIC DIRECTORY ({filteredTopics.length})
            </h2>

            {/* SEARCH AND FILTERS */}
            <div style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="Search master topics..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', padding: '6px 10px',
                  border: '1px solid #292524', backgroundColor: '#f4efe6', color: '#292524', outline: 'none'
                }}
              />
              <div style={{ display: 'flex', gap: '4px' }}>
                {['All', 'Active', 'Archived', 'Draft'].map(f => (
                  <button
                    key={f}
                    onClick={() => setStatusFilter(f)}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '700',
                      padding: '5px 8px', border: '1px solid #292524', cursor: 'pointer',
                      backgroundColor: statusFilter === f ? '#292524' : '#f4efe6',
                      color: statusFilter === f ? '#f4efe6' : '#292524',
                      textTransform: 'uppercase'
                    }}
                  >
                    {f}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {loading ? (
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: '#57534e', fontStyle: 'italic' }}>
              Loading master topics directory...
            </p>
          ) : filteredTopics.length === 0 ? (
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', color: '#57534e', fontStyle: 'italic' }}>
              No topic entities matching the specified search or filter criteria.
            </p>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
                <thead>
                  <tr style={{
                    borderBottom: '2px solid #292524', fontFamily: "'JetBrains Mono', monospace",
                    fontSize: '11px', textTransform: 'uppercase', color: '#44403c'
                  }}>
                    <th style={{ padding: '8px' }}>ID</th>
                    <th style={{ padding: '8px' }}>CATEGORY</th>
                    <th style={{ padding: '8px' }}>TOPIC DISPATCH TITLE</th>
                    <th style={{ padding: '8px' }}>SOURCE OUTLET</th>
                    <th style={{ padding: '8px' }}>STATUS</th>
                    <th style={{ padding: '8px' }}>SCORE</th>
                    <th style={{ padding: '8px' }}>STAMP TIER</th>
                    <th style={{ padding: '8px' }}>DATE</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTopics.map(topic => {
                    const score = formatScore(topic.weighted_score);
                    const tier = getTierBadge(topic.weighted_score);
                    return (
                      <tr key={topic.id} style={{ borderBottom: '1px solid #a8a29e' }}>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '700' }}>
                          #{topic.id}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '700', color: '#57534e' }}>
                          {getCategoryTag(topic)}
                        </td>
                        <td style={{ padding: '10px 8px', fontWeight: '700', color: '#292524', fontFamily: "'Georgia', serif", fontSize: '14px' }}>
                          {topic.title}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#57534e' }}>
                          {topic.source_name || topic.source || '—'}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
                          <span style={{
                            padding: '2px 6px', fontWeight: '800', border: '1px solid #292524',
                            backgroundColor: topic.status === 'published' || topic.status === 'active' ? '#292524' : '#f4efe6',
                            color: topic.status === 'published' || topic.status === 'active' ? '#f4efe6' : '#292524',
                            textTransform: 'uppercase'
                          }}>
                            {topic.status}
                          </span>
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', fontWeight: '800', color: '#292524' }}>
                          {score != null ? `${score} / 100` : '—'}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '10px' }}>
                          {tier ? (
                            <span style={{
                              padding: '2px 6px', fontWeight: '800', border: '1px solid',
                              borderColor: tier.color, color: tier.color, backgroundColor: tier.bg
                            }}>
                              [{tier.label}]
                            </span>
                          ) : '—'}
                        </td>
                        <td style={{ padding: '10px 8px', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#57534e' }}>
                          {new Date(topic.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </div>
    </div>
  );
}
