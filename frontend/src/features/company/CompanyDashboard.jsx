import React, { useState, useEffect } from 'react';
import { supabase } from '../../supabase';

function formatScore(val) {
  if (val == null) return 85;
  const num = Number(val);
  if (isNaN(num)) return 85;
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

function getStampStyle(score) {
  const isDistinction = score >= 80;
  const isMerit = score >= 60;
  return {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '10px',
    fontWeight: '800',
    padding: '2px 8px',
    border: `1.5px solid ${isDistinction ? '#991b1b' : isMerit ? '#92400e' : '#1d4ed8'}`,
    color: isDistinction ? '#991b1b' : isMerit ? '#92400e' : '#1d4ed8',
    backgroundColor: isDistinction ? '#fee2e2' : isMerit ? '#fef3c7' : '#dbeafe',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    transform: isDistinction ? 'rotate(-1deg)' : 'none',
    display: 'inline-block'
  };
}

function getStampLabel(score) {
  if (score >= 80) return 'DISTINCTION';
  if (score >= 60) return 'MERIT';
  return 'PASS';
}

export default function CompanyDashboard({ session, profile }) {
  const [topics, setTopics] = useState([]);
  const [shortlisted, setShortlisted] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);

  const filters = ['All', 'Controversy', 'Policy', 'Ethics', 'Multi-Stakeholder'];

  useEffect(() => {
    fetchTopics();
    fetchShortlisted();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchTopics = async () => {
    try {
      const { data, error: fetchErr } = await supabase
        .from('topics')
        .select('*')
        .in('status', ['active', 'published'])
        .order('created_at', { ascending: false });

      if (fetchErr) throw fetchErr;

      const normalized = (data || []).map(t => ({
        ...t,
        source: t.source_name || t.source || 'News Outlet',
        date: t.published || t.created_at,
        score: formatScore(t.weighted_score),
      }));

      setTopics(normalized);
    } catch (err) {
      console.error('Failed to fetch company topics:', err);
      setError('Failed to load topics: ' + (err.message || 'Unknown error'));
    } finally {
      setLoading(false);
    }
  };

  const fetchShortlisted = async () => {
    const { data } = await supabase
      .from('shortlisted_topics')
      .select('topic_id')
      .eq('user_id', session.user.id);
    if (data) setShortlisted(new Set(data.map(r => r.topic_id)));
  };

  const toggleShortlist = async (topicId) => {
    if (shortlisted.has(topicId)) {
      await supabase.from('shortlisted_topics')
        .delete()
        .eq('user_id', session.user.id)
        .eq('topic_id', topicId);
      setShortlisted(prev => { const s = new Set(prev); s.delete(topicId); return s; });
    } else {
      await supabase.from('shortlisted_topics')
        .insert({ user_id: session.user.id, topic_id: topicId });
      setShortlisted(prev => new Set([...prev, topicId]));
    }
  };

  const handleLogout = () => supabase.auth.signOut();

  const filteredTopics = topics.filter(t => {
    const matchSearch = t.title?.toLowerCase().includes(search.toLowerCase()) ||
                        t.summary?.toLowerCase().includes(search.toLowerCase()) ||
                        t.source?.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === 'All' ? true :
      filter === 'Controversy' ? t.controversy :
      filter === 'Policy' ? t.policy_relevance :
      filter === 'Ethics' ? t.ethical_dimension :
      filter === 'Multi-Stakeholder' ? t.multiple_stakeholders : true;
    return matchSearch && matchFilter;
  });

  const pageSize = 9;
  const totalPages = Math.max(1, Math.ceil(filteredTopics.length / pageSize));
  const currentPageTopics = filteredTopics.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  const currentDateStr = new Date().toLocaleDateString('en-US', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'
  }).toUpperCase();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f4efe6', color: '#292524', fontFamily: "'Georgia', serif", padding: '24px 40px' }}>
      <div style={{ maxWidth: '100%', margin: '0 auto' }}>

        {/* TOP MASTHEAD */}
        <header style={{
          display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          alignItems: 'center', gap: '16px', padding: '16px 0',
          borderTop: '3px double #292524', borderBottom: '3px double #292524', marginBottom: '16px'
        }}>
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#44403c', border: '1px solid #a8a29e', padding: '10px', backgroundColor: '#eae3d6' }}>
            <div style={{ fontWeight: '700' }}>DESK: CORPORATE RECRUITER</div>
            <div style={{ color: '#57534e', marginTop: '2px' }}>{currentDateStr}</div>
            <div style={{ color: '#78716c', marginTop: '2px', fontSize: '10px' }}>PAGE {currentPage} OF {totalPages}</div>
          </div>

          <div style={{ gridColumn: 'span 2', textAlign: 'center' }}>
            <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 'clamp(2.5rem, 6vw, 4.2rem)', fontWeight: '900', color: '#1c1917', margin: '0 0 4px 0', lineHeight: 1.0, letterSpacing: '-0.02em' }}>
              The AIDE Daily
            </h1>
            <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.15em', color: '#57534e', margin: 0, fontWeight: '700' }}>
              CAMPUS RECRUITMENT DRIVE INTELLIGENCE · EST. 2026
            </p>
          </div>

          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#44403c', border: '1px solid #a8a29e', padding: '10px', backgroundColor: '#eae3d6', textAlign: 'right' }}>
            <div style={{ fontWeight: '700', color: '#1c1917' }}>{profile?.full_name || session.user.email}</div>
            <div style={{ color: '#166534', fontWeight: '700', marginTop: '2px', display: 'flex', justifyContent: 'flex-end', gap: '8px', alignItems: 'center' }}>
              <span>{shortlisted.size} SHORTLISTED</span>
              <span>·</span>
              <button onClick={handleLogout} style={{ background: 'none', border: 'none', color: '#991b1b', fontWeight: '700', cursor: 'pointer', textDecoration: 'underline' }}>[ LOGOUT ]</button>
            </div>
          </div>
        </header>

        {/* SECTION NAVIGATION */}
        <nav style={{
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center',
          gap: '16px', paddingBottom: '12px', borderBottom: '2px solid #292524', marginBottom: '24px',
          fontFamily: "'JetBrains Mono', monospace", fontSize: '12px'
        }}>
          <div style={{ display: 'flex', gap: '20px', fontWeight: '700' }}>
            <span style={{ color: '#78716c' }}>§ DISPATCHES</span>
            <span style={{ color: '#78716c' }}>§ APTITUDE & ASSESSMENT</span>
            <span style={{ borderBottom: '2px solid #292524', paddingBottom: '2px', color: '#1c1917' }}>§ COMPANY INTELLIGENCE</span>
          </div>
        </nav>

        {/* SEARCH & FILTERS */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', marginBottom: '24px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px' }}>
          <div style={{ flex: 1, minWidth: '260px', display: 'flex', alignItems: 'center', backgroundColor: '#eae3d6', border: '1px solid #a8a29e', padding: '6px 12px', gap: '8px' }}>
            <span style={{ color: '#57534e', fontWeight: '700' }}>SEARCH RECRUITMENT TOPICS:</span>
            <input
              placeholder="enter topic, source, or summary..."
              value={search}
              onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
              style={{ border: 'none', outline: 'none', fontSize: '12px', width: '100%', backgroundColor: 'transparent', color: '#1c1917', fontFamily: "'Georgia', serif", fontStyle: 'italic' }}
            />
          </div>

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {filters.map(f => (
              <button key={f} onClick={() => { setFilter(f); setCurrentPage(1); }} style={{
                padding: '4px 10px', border: '1px solid #292524',
                backgroundColor: filter === f ? '#292524' : '#eae3d6',
                color: filter === f ? '#f4efe6' : '#292524',
                fontWeight: '700', fontSize: '11px', cursor: 'pointer', textTransform: 'uppercase'
              }}>
                {f}
              </button>
            ))}
          </div>
        </div>

        {error && <div style={{ padding: '12px', backgroundColor: '#fee2e2', border: '2px solid #991b1b', color: '#991b1b', fontFamily: "'JetBrains Mono', monospace", marginBottom: '20px' }}>✖ {error}</div>}
        {loading && <p style={{ fontFamily: "'JetBrains Mono', monospace", color: '#57534e' }}>Loading recruitment dispatches...</p>}

        {!loading && (
          <div>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
              gap: '28px',
              alignItems: 'stretch'
            }}>
              {currentPageTopics.map(topic => (
                <article key={topic.id} style={{
                  border: shortlisted.has(topic.id) ? '2px solid #166534' : '1px solid #a8a29e',
                  backgroundColor: shortlisted.has(topic.id) ? '#f0fdf4' : '#eae3d6',
                  padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'
                }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '700', color: '#57534e', textTransform: 'uppercase' }}>
                        {getCategoryTag(topic)}
                      </span>
                      <span style={getStampStyle(topic.score)}>
                        [{getStampLabel(topic.score)}]
                      </span>
                    </div>

                    <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: '20px', fontWeight: '700', color: '#1c1917', margin: '0 0 8px 0', lineHeight: 1.3 }}>
                      {topic.title}
                    </h3>

                    <p style={{ fontSize: '13px', color: '#44403c', margin: '0 0 16px 0', lineHeight: 1.5 }}>
                      {topic.summary}
                    </p>
                  </div>

                  <div style={{ borderTop: '1px solid #a8a29e', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
                    <span style={{ color: '#1c1917', fontWeight: '800' }}>SCORE {topic.score} / 100</span>
                    <button
                      onClick={() => toggleShortlist(topic.id)}
                      style={{
                        fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '800',
                        padding: '4px 10px', border: '1px solid #292524',
                        backgroundColor: shortlisted.has(topic.id) ? '#166534' : 'transparent',
                        color: shortlisted.has(topic.id) ? '#f4efe6' : '#292524',
                        cursor: 'pointer', textTransform: 'uppercase'
                      }}
                    >
                      {shortlisted.has(topic.id) ? '[ 🔖 SHORTLISTED ]' : '[ SHORTLIST → ]'}
                    </button>
                  </div>
                </article>
              ))}
            </div>

            {/* NEWSPAPER PAGINATION CONTROL BAR */}
            {totalPages > 1 && (
              <div style={{
                borderTop: '3px double #292524', borderBottom: '3px double #292524',
                padding: '14px 20px', marginTop: '40px', marginBottom: '24px', display: 'flex', flexWrap: 'wrap',
                justify: 'space-between', alignItems: 'center', gap: '16px',
                fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', backgroundColor: '#eae3d6'
              }}>
                <div style={{ fontWeight: '800', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#1c1917' }}>
                  § EDITION PAGES: PAGE {currentPage} OF {totalPages} ({filteredTopics.length} TOTAL DISPATCHES)
                </div>

                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
                  <button
                    onClick={() => { setCurrentPage(prev => Math.max(1, prev - 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    disabled={currentPage === 1}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800',
                      padding: '6px 12px', border: '1px solid #292524', cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                      backgroundColor: currentPage === 1 ? '#d6cebf' : '#292524',
                      color: currentPage === 1 ? '#78716c' : '#f4efe6', textTransform: 'uppercase'
                    }}
                  >
                    [ ← PREV PAGE ]
                  </button>

                  {Array.from({ length: totalPages }, (_, i) => i + 1).map(pageNum => (
                    <button
                      key={pageNum}
                      onClick={() => { setCurrentPage(pageNum); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                      style={{
                        fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800',
                        padding: '6px 12px', border: '1px solid #292524', cursor: 'pointer',
                        backgroundColor: currentPage === pageNum ? '#292524' : '#eae3d6',
                        color: currentPage === pageNum ? '#f4efe6' : '#292524', textTransform: 'uppercase'
                      }}
                    >
                      [ PAGE {pageNum} ]
                    </button>
                  ))}

                  <button
                    onClick={() => { setCurrentPage(prev => Math.min(totalPages, prev + 1)); window.scrollTo({ top: 0, behavior: 'smooth' }); }}
                    disabled={currentPage === totalPages}
                    style={{
                      fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800',
                      padding: '6px 12px', border: '1px solid #292524', cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                      backgroundColor: currentPage === totalPages ? '#d6cebf' : '#292524',
                      color: currentPage === totalPages ? '#78716c' : '#f4efe6', textTransform: 'uppercase'
                    }}
                  >
                    [ NEXT PAGE → ]
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}