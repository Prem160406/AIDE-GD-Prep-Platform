import React, { useState, useEffect } from 'react';
import { supabase } from './supabase';
import AuthPage from './features/auth/AuthPage';
import StudentDashboard from './features/student/StudentDashboard';
import TPODashboard from './features/tpo/TPODashboard';
import CompanyDashboard from './features/company/CompanyDashboard';

function App() {
  const [session, setSession] = useState(null);
  const [role, setRole] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setRole(session?.user?.user_metadata?.role || null);
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setRole(session?.user?.user_metadata?.role || null);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: '#6b7280', fontSize: '16px' }}>Loading...</p>
    </div>
  );

  if (!session) return <AuthPage />;

  if (role === 'student') return <StudentDashboard session={session} />;
  if (role === 'tpo') return <TPODashboard session={session} />;
  if (role === 'company') return <CompanyDashboard session={session} />;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p style={{ color: '#dc2626' }}>Unknown role. Contact admin.</p>
    </div>
  );
}

export default App;