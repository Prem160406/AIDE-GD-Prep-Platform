import React, { useState } from 'react';
import { supabase } from '../../supabase';

export default function AuthPage() {
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('student');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) setError(error.message);
    setLoading(false);
  };

  const handleSignup = async () => {
    if (!fullName.trim()) { setError('Full name is required'); return; }
    setLoading(true);
    setError(null);
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, role }
      }
    });
    if (error) setError(error.message);
    else setError('Check your email to confirm your account.');
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0f766e 0%, #0e7490 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
    }}>
      <div style={{
        background: '#fff',
        borderRadius: '16px',
        padding: '40px',
        width: '100%',
        maxWidth: '420px',
        boxShadow: '0 20px 40px rgba(0,0,0,0.2)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{ fontSize: '28px', fontWeight: '800', color: '#0f766e', margin: 0 }}>AIDE</h1>
          <p style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>Automated Intelligent Discussion Engine</p>
        </div>

        {/* Toggle */}
        <div style={{ display: 'flex', background: '#f3f4f6', borderRadius: '8px', padding: '4px', marginBottom: '24px' }}>
          {['login', 'signup'].map(m => (
            <button key={m} onClick={() => { setMode(m); setError(null); }} style={{
              flex: 1,
              padding: '8px',
              border: 'none',
              borderRadius: '6px',
              fontWeight: '600',
              fontSize: '14px',
              cursor: 'pointer',
              background: mode === m ? '#fff' : 'transparent',
              color: mode === m ? '#0f766e' : '#6b7280',
              boxShadow: mode === m ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              transition: 'all 0.2s',
            }}>
              {m === 'login' ? 'Log In' : 'Sign Up'}
            </button>
          ))}
        </div>

        {/* Fields */}
        {mode === 'signup' && (
          <input
            placeholder="Full Name"
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            style={inputStyle}
          />
        )}
        <input
          placeholder="Email"
          type="email"
          value={email}
          onChange={e => setEmail(e.target.value)}
          style={inputStyle}
        />
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={inputStyle}
        />

        {mode === 'signup' && (
          <select value={role} onChange={e => setRole(e.target.value)} style={inputStyle}>
            <option value="student">Student</option>
            <option value="tpo">TPO</option>
            <option value="company">Company</option>
          </select>
        )}

        {error && (
          <p style={{ fontSize: '13px', color: error.includes('Check') ? '#059669' : '#dc2626', marginBottom: '12px' }}>
            {error}
          </p>
        )}

        <button
          onClick={mode === 'login' ? handleLogin : handleSignup}
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px',
            background: loading ? '#99f6e4' : '#0f766e',
            color: '#fff',
            border: 'none',
            borderRadius: '8px',
            fontWeight: '700',
            fontSize: '15px',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'background 0.2s',
          }}
        >
          {loading ? 'Please wait...' : mode === 'login' ? 'Log In' : 'Create Account'}
        </button>
      </div>
    </div>
  );
}

const inputStyle = {
  width: '100%',
  padding: '12px',
  marginBottom: '12px',
  border: '1px solid #e5e7eb',
  borderRadius: '8px',
  fontSize: '14px',
  outline: 'none',
  boxSizing: 'border-box',
};