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
      backgroundColor: '#f4efe6',
      color: '#292524',
      fontFamily: "'Georgia', serif",
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
    }}>
      <div style={{
        backgroundColor: '#f9f6f0',
        border: '3px double #292524',
        padding: '40px',
        width: '100%',
        maxWidth: '460px',
        boxShadow: '0 10px 25px rgba(0,0,0,0.08)',
      }}>
        {/* Masthead Header */}
        <div style={{ textAlign: 'center', marginBottom: '32px', borderBottom: '2px solid #292524', paddingBottom: '16px' }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '11px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            color: '#57534e',
            marginBottom: '4px'
          }}>
            PRESS PASS & SUBSCRIPTION
          </div>
          <h1 style={{
            fontFamily: "'Playfair Display', serif",
            fontSize: '38px',
            fontWeight: '900',
            color: '#1c1917',
            margin: '0 0 4px 0',
            lineHeight: 1.1,
          }}>
            The AIDE Daily
          </h1>
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '10px',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            color: '#78716c',
            margin: 0,
          }}>
            ALL THE INTELLIGENCE FIT TO PRACTICE
          </p>
        </div>

        {/* Toggle */}
        <div style={{
          display: 'flex',
          border: '1px solid #292524',
          marginBottom: '28px',
          backgroundColor: '#e7e0d3'
        }}>
          {['login', 'signup'].map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(null); }}
              style={{
                flex: 1,
                padding: '10px',
                border: 'none',
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: '700',
                fontSize: '12px',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                cursor: 'pointer',
                backgroundColor: mode === m ? '#292524' : 'transparent',
                color: mode === m ? '#f4efe6' : '#57534e',
                transition: 'all 0.15s ease-in-out',
              }}
            >
              {m === 'login' ? '[ LOG IN ]' : '[ SIGN UP ]'}
            </button>
          ))}
        </div>

        {/* Form Fields */}
        {mode === 'signup' && (
          <div style={{ marginBottom: '16px' }}>
            <label style={labelStyle}>SUBSCRIBER FULL NAME</label>
            <input
              placeholder="e.g. Prem Salunkhe"
              value={fullName}
              onChange={e => setFullName(e.target.value)}
              style={inputStyle}
            />
          </div>
        )}

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>EMAIL ADDRESS</label>
          <input
            placeholder="name@institution.edu"
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            style={inputStyle}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={labelStyle}>SECURITY CREDENTIAL / PASSWORD</label>
          <input
            placeholder="••••••••••••"
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            style={inputStyle}
          />
        </div>

        {mode === 'signup' && (
          <div style={{ marginBottom: '20px' }}>
            <label style={labelStyle}>READER ROLE & DESK</label>
            <select value={role} onChange={e => setRole(e.target.value)} style={inputStyle}>
              <option value="student">Student / GD Aspirant</option>
              <option value="tpo">Training & Placement Officer (TPO)</option>
              <option value="company">Corporate Recruiter</option>
            </select>
          </div>
        )}

        {error && (
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '12px',
            padding: '10px 14px',
            border: `1px solid ${error.includes('Check') ? '#166534' : '#991b1b'}`,
            backgroundColor: error.includes('Check') ? '#dcfce7' : '#fee2e2',
            color: error.includes('Check') ? '#166534' : '#991b1b',
            marginBottom: '16px',
          }}>
            {error}
          </div>
        )}

        <button
          onClick={mode === 'login' ? handleLogin : handleSignup}
          disabled={loading}
          style={{
            width: '100%',
            padding: '12px',
            backgroundColor: loading ? '#78716c' : '#292524',
            color: '#f4efe6',
            border: '1px solid #292524',
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: '700',
            fontSize: '13px',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.15s ease-in-out',
          }}
        >
          {loading ? '[ PROCESSING... ]' : mode === 'login' ? '[ ACCESS DISPATCHES → ]' : '[ CREATE PRESS PASS → ]'}
        </button>

        <div style={{
          marginTop: '28px',
          textAlign: 'center',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '10px',
          color: '#78716c',
          borderTop: '1px solid #d6cebf',
          paddingTop: '16px',
        }}>
          AIDE DISPATCH SYSTEM · EDITION 2026
        </div>
      </div>
    </div>
  );
}

const labelStyle = {
  display: 'block',
  fontFamily: "'JetBrains Mono', monospace",
  fontSize: '11px',
  fontWeight: '700',
  color: '#44403c',
  marginBottom: '6px',
  letterSpacing: '0.05em',
};

const inputStyle = {
  width: '100%',
  padding: '10px 12px',
  border: '1px solid #a8a29e',
  backgroundColor: '#f4efe6',
  color: '#1c1917',
  fontFamily: "'Georgia', serif",
  fontSize: '14px',
  outline: 'none',
  boxSizing: 'border-box',
};