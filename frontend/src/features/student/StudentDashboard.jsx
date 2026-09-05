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
  if (text.includes('ai') || text.includes('tech') || text.includes('digital') || text.includes('cyber') || text.includes('data') || text.includes('model') || text.includes('generative')) {
    return '⚡ TECH & INNOVATION';
  }
  if (text.includes('econ') || text.includes('esg') || text.includes('bank') || text.includes('fiscal') || text.includes('market') || text.includes('trade') || text.includes('poverty') || text.includes('income') || text.includes('financial')) {
    return '📊 ECONOMICS & BUSINESS';
  }
  if (text.includes('policy') || text.includes('gov') || text.includes('parliament') || text.includes('india') || text.includes('state') || text.includes('law') || text.includes('court') || text.includes('mandate')) {
    return '🏛️ POLICY & GOVERNANCE';
  }
  if (text.includes('ethic') || text.includes('social') || text.includes('privacy') || text.includes('climate') || text.includes('rights') || text.includes('transparency')) {
    return '⚖️ ETHICS & SOCIETY';
  }
  if (text.includes('world') || text.includes('global') || text.includes('foreign') || text.includes('us') || text.includes('china') || text.includes('war') || text.includes('sovereignty')) {
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

export default function StudentDashboard({ session, profile }) {
  const [topics, setTopics] = useState([]);
  const [practiced, setPracticed] = useState(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  useEffect(() => {
    fetchTopics();
    fetchPracticed();
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
      console.error('Failed to fetch topics:', err);
      setError('Failed to load topics: ' + (err.message || 'Unknown error'));
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

  const handleLogout = () => supabase.auth.signOut();

  const filteredTopics = topics.filter(t =>
    t.title?.toLowerCase().includes(search.toLowerCase()) ||
    t.summary?.toLowerCase().includes(search.toLowerCase()) ||
    t.source?.toLowerCase().includes(search.toLowerCase())
  );

  // Lead story is highest score dispatch overall
  const leadStory = filteredTopics.length > 0
    ? [...filteredTopics].sort((a, b) => b.score - a.score)[0]
    : null;

  const secondaryTopics = filteredTopics.filter(t => t.id !== leadStory?.id);

  // Pagination Logic: Page 1 has 1 Lead + 6 Secondary (total 7); subsequent pages have 8 dispatches
  const totalPages = Math.max(1, Math.ceil((secondaryTopics.length - 6) / 8) + 1);

  // Calculate slice for current page
  let currentPageSecondary = [];
  if (currentPage === 1) {
    currentPageSecondary = secondaryTopics.slice(0, 6);
  } else {
    const startIdx = 6 + (currentPage - 2) * 8;
    currentPageSecondary = secondaryTopics.slice(startIdx, startIdx + 8);
  }

  const sidebarTopics = currentPage === 1 ? currentPageSecondary.slice(0, 3) : [];
  const gridTopics = currentPage === 1 ? currentPageSecondary.slice(3) : currentPageSecondary;

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
          {/* Left Metadata */}
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#44403c',
            border: '1px solid #a8a29e', padding: '10px', backgroundColor: '#eae3d6'
          }}>
            <div style={{ fontWeight: '700' }}>VOL. I · NO. {topics.length || 143}</div>
            <div style={{ color: '#57534e', marginTop: '2px' }}>{currentDateStr}</div>
            <div style={{ color: '#78716c', marginTop: '2px', fontSize: '10px' }}>EDITION: FRONT PAGE · PAGE {currentPage} OF {totalPages}</div>
          </div>

          {/* Center Title */}
          <div style={{ gridColumn: 'span 2', textAlign: 'center' }}>
            <h1 style={{
              fontFamily: "'Playfair Display', serif", fontSize: 'clamp(2.5rem, 6vw, 4.2rem)',
              fontWeight: '900', color: '#1c1917', margin: '0 0 4px 0', lineHeight: 1.0, letterSpacing: '-0.02em'
            }}>
              The AIDE Daily
            </h1>
            <p style={{
              fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', textTransform: 'uppercase',
              letterSpacing: '0.15em', color: '#57534e', margin: 0, fontWeight: '700'
            }}>
              ALL THE INTELLIGENCE FIT TO PRACTICE · EST. 2026
            </p>
          </div>

          {/* Right User Bar */}
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#44403c',
            border: '1px solid #a8a29e', padding: '10px', backgroundColor: '#eae3d6', textAlign: 'right'
          }}>
            <div style={{ fontWeight: '700', color: '#1c1917' }}>
              {profile?.full_name || session.user.email}
            </div>
            <div style={{ color: '#166534', fontWeight: '700', marginTop: '2px', display: 'flex', justifyContent: 'flex-end', gap: '8px', alignItems: 'center' }}>
              <span>{practiced.size} PRACTICED</span>
              <span>·</span>
              <button
                onClick={handleLogout}
                style={{
                  fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '700',
                  backgroundColor: 'transparent', border: '1px solid #292524', padding: '2px 6px',
                  cursor: 'pointer', color: '#991b1b', textTransform: 'uppercase'
                }}
              >
                [ LOGOUT ]
              </button>
            </div>
          </div>
        </header>

        {/* SECTION NAVIGATION & LIVE SEARCH */}
        <nav style={{
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center',
          gap: '16px', paddingBottom: '12px', borderBottom: '2px solid #292524', marginBottom: '24px',
          fontFamily: "'JetBrains Mono', monospace", fontSize: '12px'
        }}>
          <div style={{ display: 'flex', gap: '20px', fontWeight: '700' }}>
            <span style={{ borderBottom: '2px solid #292524', paddingBottom: '2px', color: '#1c1917' }}>§ DISPATCHES</span>
            <span style={{ color: '#78716c' }}>§ APTITUDE & ASSESSMENT</span>
            <span style={{ color: '#78716c' }}>§ COMPANY INTELLIGENCE</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: '1', maxWidth: '420px', justifyContent: 'flex-end' }}>
            <span style={{ fontSize: '11px', color: '#57534e', textTransform: 'uppercase', letterSpacing: '0.05em', whiteSpace: 'nowrap' }}>SEARCH DISPATCHES:</span>
            <input
              placeholder="enter topic, source, or category..."
              value={search}
              onChange={e => { setSearch(e.target.value); setCurrentPage(1); }}
              style={{
                backgroundColor: '#eae3d6', border: '1px solid #a8a29e', padding: '5px 10px',
                fontSize: '12px', color: '#1c1917', outline: 'none', fontFamily: "'Georgia', serif",
                fontStyle: 'italic', width: '100%'
              }}
            />
          </div>
        </nav>

        {error && (
          <div style={{
            padding: '12px', backgroundColor: '#fee2e2', border: '2px solid #991b1b',
            color: '#991b1b', fontFamily: "'JetBrains Mono', monospace", fontSize: '13px', fontWeight: '700', marginBottom: '20px'
          }}>
            ✖ {error}
          </div>
        )}

        {loading && <p style={{ fontFamily: "'JetBrains Mono', monospace", color: '#57534e', fontSize: '13px' }}>Printing dispatches from Supabase engine...</p>}

        {!loading && (
          <div>

            {/* PAGE 1: HERO LEAD STORY & SIDEBAR */}
            {currentPage === 1 && leadStory && (
              <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '36px', borderBottom: '3px double #292524', paddingBottom: '36px', marginBottom: '36px' }}>
                
                {/* LEAD FEATURE STORY */}
                <article style={{ flex: '2', minWidth: '340px', borderRight: '1px solid #a8a29e', paddingRight: '28px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800', textTransform: 'uppercase', color: '#44403c', letterSpacing: '0.08em' }}>
                      {getCategoryTag(leadStory)}
                    </span>
                    <span style={getStampStyle(leadStory.score)}>
                      [{getStampLabel(leadStory.score)}]
                    </span>
                  </div>

                  <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: 'clamp(2rem, 4vw, 3.2rem)', fontWeight: '900', color: '#1c1917', margin: '0 0 12px 0', lineHeight: 1.12 }}>
                    {leadStory.title}
                  </h2>

                  <p style={{ fontStyle: 'italic', color: '#44403c', fontSize: '16px', borderBottom: '1px solid #a8a29e', paddingBottom: '14px', marginBottom: '18px', lineHeight: 1.5 }}>
                    {leadStory.summary}
                  </p>

                  {/* Two Column Newspaper Body Text */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '24px', fontSize: '14px', lineHeight: 1.65, textAlign: 'justify', color: '#292524', marginBottom: '28px' }}>
                    <p style={{ margin: 0 }}>
                      The proposition of this discussion dispatch has moved from academic abstraction to live policy debate as structural transformation accelerates across key global sectors. Proponents argue a minimum baseline security reduces systemic vulnerability and enables entrepreneurial risk-taking; critics contend the fiscal arithmetic remains untenable without fundamental structural reform.
                    </p>
                    <p style={{ margin: 0 }}>
                      As institutional frameworks evaluate safety-net structures, key evaluation parameters prioritize controversy, multiple stakeholder impacts, factual freshness, and ethical clarity. Group discussion participants must examine whether systematic intervention provides higher long-term stability than targeted regulatory measures.
                    </p>
                  </div>

                  {/* Lead Story Footer Bar */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', borderTop: '2px solid #292524', paddingTop: '14px', fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', gap: '12px' }}>
                    <div style={{ color: '#57534e' }}>
                      <strong style={{ color: '#1c1917' }}>{leadStory.source.toUpperCase()}</strong> · {leadStory.date ? new Date(leadStory.date).toLocaleDateString().toUpperCase() : 'TODAY'}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <span style={{ fontWeight: '800', color: '#1c1917', borderBottom: '1px solid #292524', fontSize: '14px' }}>
                        SCORE {leadStory.score} / 100
                      </span>
                      <button
                        onClick={() => togglePracticed(leadStory.id)}
                        style={{
                          fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800',
                          padding: '6px 14px', border: '1px solid #292524', cursor: 'pointer',
                          backgroundColor: practiced.has(leadStory.id) ? '#166534' : 'transparent',
                          color: practiced.has(leadStory.id) ? '#f4efe6' : '#292524', textTransform: 'uppercase'
                        }}
                      >
                        {practiced.has(leadStory.id) ? '[ ✓ PRACTICED ]' : '[ PRACTICE → ]'}
                      </button>
                    </div>
                  </div>
                </article>

                {/* SIDEBAR DISPATCHES */}
                <aside style={{ flex: '1', minWidth: '300px', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', fontWeight: '800', borderBottom: '2px solid #292524', paddingBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#57534e' }}>
                    § FRONT PAGE EDITORIAL DISPATCHES
                  </div>
                  {sidebarTopics.map(topic => (
                    <article key={topic.id} style={{ borderBottom: '1px solid #a8a29e', paddingBottom: '18px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                        <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '700', color: '#57534e', textTransform: 'uppercase' }}>
                          {getCategoryTag(topic)}
                        </span>
                        <span style={getStampStyle(topic.score)}>
                          [{getStampLabel(topic.score)}]
                        </span>
                      </div>

                      <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: '19px', fontWeight: '700', color: '#1c1917', margin: '0 0 6px 0', lineHeight: 1.3 }}>
                        {topic.title}
                      </h3>

                      <p style={{ fontSize: '12px', color: '#44403c', margin: '0 0 10px 0', lineHeight: 1.45, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                        {topic.summary}
                      </p>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
                        <span style={{ color: '#57534e', fontWeight: '700' }}>
                          SCORE {topic.score} / 100
                        </span>
                        <button
                          onClick={() => togglePracticed(topic.id)}
                          style={{
                            fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '800',
                            padding: '4px 8px', border: '1px solid #292524', cursor: 'pointer',
                            backgroundColor: practiced.has(topic.id) ? '#166534' : 'transparent',
                            color: practiced.has(topic.id) ? '#f4efe6' : '#292524', textTransform: 'uppercase'
                          }}
                        >
                          {practiced.has(topic.id) ? '[ ✓ PRACTICED ]' : '[ PRACTICE ]'}
                        </button>
                      </div>
                    </article>
                  ))}
                </aside>
              </section>
            )}

            {/* PAGE BANNER FOR SUBSEQUENT PAGES */}
            {currentPage > 1 && (
              <div style={{
                borderBottom: '2px solid #292524', paddingBottom: '8px', marginBottom: '24px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center'
              }}>
                <h2 style={{ fontFamily: "'Playfair Display', serif", fontSize: '24px', fontWeight: '800', textTransform: 'uppercase', margin: 0 }}>
                  § THE AIDE DAILY · PAGE {currentPage}: CONTINUED DISPATCHES & OP-EDS
                </h2>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: '#57534e', fontWeight: '700' }}>
                  SHOWING ITEMS {6 + (currentPage - 2) * 8 + 1}–{Math.min(secondaryTopics.length, 6 + (currentPage - 1) * 8)} OF {filteredTopics.length}
                </span>
              </div>
            )}

            {/* FLEXIBLE MASONRY NEWSPAPER GRID */}
            {gridTopics.length > 0 && (
              <section>
                {currentPage === 1 && (
                  <div style={{ borderBottom: '2px solid #292524', paddingBottom: '6px', marginBottom: '24px' }}>
                    <h3 style={{ fontFamily: "'Playfair Display', serif", fontSize: '22px', fontWeight: '800', textTransform: 'uppercase', margin: 0 }}>
                      § ADDITIONAL DISPATCHES & DEBATE TOPICS
                    </h3>
                  </div>
                )}

                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))',
                  gap: '28px',
                  alignItems: 'stretch'
                }}>
                  {gridTopics.map(topic => (
                    <article key={topic.id} style={{
                      border: '1px solid #a8a29e', backgroundColor: '#eae3d6', padding: '20px',
                      display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                      transition: 'all 0.15s ease'
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

                        <h4 style={{ fontFamily: "'Playfair Display', serif", fontSize: '20px', fontWeight: '700', color: '#1c1917', margin: '0 0 8px 0', lineHeight: 1.3 }}>
                          {topic.title}
                        </h4>

                        <p style={{ fontSize: '13px', color: '#44403c', margin: '0 0 16px 0', lineHeight: 1.5 }}>
                          {topic.summary}
                        </p>
                      </div>

                      <div style={{ borderTop: '1px solid #a8a29e', paddingTop: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontFamily: "'JetBrains Mono', monospace", fontSize: '11px' }}>
                        <span style={{ color: '#57534e', fontWeight: '700' }}>
                          {topic.source.toUpperCase()} · SCORE {topic.score} / 100
                        </span>
                        <button
                          onClick={() => togglePracticed(topic.id)}
                          style={{
                            fontFamily: "'JetBrains Mono', monospace", fontSize: '10px', fontWeight: '800',
                            padding: '4px 8px', border: '1px solid #292524', cursor: 'pointer',
                            backgroundColor: practiced.has(topic.id) ? '#166534' : 'transparent',
                            color: practiced.has(topic.id) ? '#f4efe6' : '#292524', textTransform: 'uppercase'
                          }}
                        >
                          {practiced.has(topic.id) ? '[ ✓ PRACTICED ]' : '[ PRACTICE ]'}
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            )}

            {filteredTopics.length === 0 && (
              <p style={{ fontFamily: "'JetBrains Mono', monospace", color: '#57534e', fontSize: '13px' }}>No dispatches match your search query.</p>
            )}

            {/* NEWSPAPER PAGINATION CONTROL BAR */}
            {totalPages > 1 && (
              <div style={{
                borderTop: '3px double #292524', borderBottom: '3px double #292524',
                padding: '14px 20px', marginTop: '40px', marginBottom: '24px', display: 'flex', flexWrap: 'wrap',
                justifyContent: 'space-between', alignItems: 'center', gap: '16px',
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

        {/* FOOTER MASTHEAD LINE */}
        <footer style={{
          marginTop: '48px', paddingTop: '16px', borderTop: '2px solid #292524',
          display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center',
          fontFamily: "'JetBrains Mono', monospace", fontSize: '11px', color: '#57534e', gap: '12px'
        }}>
          <div>THE AIDE DAILY · AUTOMATED INTELLIGENT DISCUSSION ENGINE</div>
          <div>PRINTED FROM SUPABASE ENGINE</div>
        </footer>

      </div>
    </div>
  );
}