import React, { useState, useEffect } from 'react';
import { supabase } from './supabase';
import AuthPage from './features/auth/AuthPage';
import StudentDashboard from './features/student/StudentDashboard';
import TPODashboard from './features/tpo/TPODashboard';
import CompanyDashboard from './features/company/CompanyDashboard';
import MasterAdminDashboard from './features/admin/MasterAdminDashboard';

function App() {
  const [session, setSession] = useState(null);
  const [role, setRole] = useState(null);
  const [profile, setProfile] = useState(null);
  const [systemStatus, setSystemStatus] = useState({ is_live: true, message: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSystemStatus();

    // Realtime subscription for system_status maintenance toggle
    const statusSub = supabase
      .channel('public:system_status_app')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'system_status' }, (payload) => {
        if (payload.new) setSystemStatus(payload.new);
      })
      .subscribe();

    async function loadUserProfile(currentSession) {
      if (!currentSession) {
        setSession(null);
        setRole(null);
        setProfile(null);
        setLoading(false);
        return;
      }
      setSession(currentSession);
      try {
        const { data: userProfile, error } = await supabase
          .from('profiles')
          .select('role, full_name')
          .eq('id', currentSession.user.id)
          .maybeSingle();

        if (error || !userProfile) {
          console.warn('Profile fetch warning, fallback to user_metadata:', error?.message);
          setRole(currentSession.user?.user_metadata?.role || 'student');
          setProfile({ full_name: currentSession.user?.user_metadata?.full_name || currentSession.user.email });
        } else {
          setRole(userProfile.role);
          setProfile(userProfile);
        }
      } catch (err) {
        console.error('Error fetching user profile:', err);
        setRole('student');
      } finally {
        setLoading(false);
      }
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      loadUserProfile(session);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      loadUserProfile(session);
    });

    return () => {
      subscription.unsubscribe();
      supabase.removeChannel(statusSub);
    };
  }, []);

  const fetchSystemStatus = async () => {
    try {
      const { data } = await supabase.from('system_status').select('*').eq('id', 1).maybeSingle();
      if (data) setSystemStatus(data);
    } catch (err) {
      console.warn('System status fetch failed:', err);
    }
  };

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: '#6b7280', fontSize: '16px' }}>Loading...</p>
    </div>
  );

  if (!session) return <AuthPage />;

  // Maintenance Overlay for non-admin users when system is taken offline
  if (!systemStatus.is_live && role !== 'admin') {
    return (
      <div style={{
        minHeight: '100vh', background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px', color: '#fff'
      }}>
        <div style={{
          background: 'rgba(255,255,255,0.05)', borderRadius: '16px', padding: '40px',
          maxWidth: '480px', width: '100%', border: '1px solid rgba(255,255,255,0.1)', textAlign: 'center'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '16px' }}>🛠️</div>
          <h2 style={{ fontSize: '24px', fontWeight: '800', marginBottom: '12px', color: '#38bdf8' }}>System Maintenance</h2>
          <p style={{ fontSize: '15px', color: '#cbd5e1', lineHeight: 1.6, marginBottom: '24px' }}>
            {systemStatus.message || 'AIDE is currently offline for scheduled maintenance. Please check back shortly.'}
          </p>
          <button
            onClick={() => supabase.auth.signOut()}
            style={{
              padding: '10px 20px', background: '#334155', color: '#fff', border: 'none',
              borderRadius: '8px', fontWeight: '600', cursor: 'pointer', fontSize: '14px'
            }}
          >
            Log Out
          </button>
        </div>
      </div>
    );
  }

  if (role === 'admin') return <MasterAdminDashboard session={session} profile={profile} />;
  if (role === 'student') return <StudentDashboard session={session} profile={profile} />;
  if (role === 'tpo') return <TPODashboard session={session} profile={profile} />;
  if (role === 'company') return <CompanyDashboard session={session} profile={profile} />;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: '#dc2626' }}>Unknown role. Contact admin.</p>
    </div>
  );
}

export default App;