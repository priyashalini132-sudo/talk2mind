import React, { useState } from 'react';
import { BrainCircuit, Mail, Lock, User as UserIcon } from 'lucide-react';

export default function Auth({ setToken, API_BASE_URL }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (isLogin) {
        // Form encoded body for OAuth2PasswordRequestForm
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const res = await fetch(`${API_BASE_URL}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: formData.toString()
        });

        const data = await res.json();
        if (res.ok) {
          setToken(data.access_token);
        } else {
          setError(data.detail || 'Login failed. Please verify credentials.');
        }
      } else {
        const res = await fetch(`${API_BASE_URL}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username,
            email,
            full_name: fullName,
            password
          })
        });

        const data = await res.json();
        if (res.ok) {
          // Auto login after signup
          setIsLogin(true);
          const formData = new URLSearchParams();
          formData.append('username', username);
          formData.append('password', password);

          const loginRes = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData.toString()
          });
          const loginData = await loginRes.json();
          if (loginRes.ok) {
            setToken(loginData.access_token);
          }
        } else {
          setError(data.detail || 'Registration failed. Try a different username/email.');
        }
      }
    } catch (err) {
      console.error(err);
      setError('Connection to backend failed. Make sure FastAPI server is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#0a0b10',
      backgroundImage: 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.15) 0%, transparent 60%)',
      padding: '2rem'
    }}>
      <div className="glass-panel animated-view" style={{ maxWidth: '420px', width: '100%', padding: '2.5rem' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <div className="logo-icon" style={{ display: 'inline-flex', padding: '10px', marginBottom: '1rem' }}>
            <BrainCircuit size={28} color="#fff" />
          </div>
          <h2 style={{ fontSize: '1.75rem', marginBottom: '0.5rem', color: '#fff' }}>
            {isLogin ? 'Welcome to Talk2Mind' : 'Create Account'}
          </h2>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            {isLogin ? 'Sign in to access your mental well-being companion' : 'Begin your guided cognitive diagnostics journey'}
          </p>
        </div>

        {error && (
          <div style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            borderRadius: '10px',
            padding: '0.8rem',
            color: '#f87171',
            fontSize: '0.85rem',
            marginBottom: '1.5rem',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label className="input-label">Username</label>
            <div style={{ position: 'relative' }}>
              <UserIcon size={16} style={{ position: 'absolute', left: '12px', top: '15px', color: '#64748b' }} />
              <input
                type="text"
                className="input-field"
                placeholder="demo"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ paddingLeft: '2.5rem', width: '100%' }}
                required
              />
            </div>
          </div>

          {!isLogin && (
            <>
              <div className="input-group">
                <label className="input-label">Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail size={16} style={{ position: 'absolute', left: '12px', top: '15px', color: '#64748b' }} />
                  <input
                    type="email"
                    className="input-field"
                    placeholder="email@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{ paddingLeft: '2.5rem', width: '100%' }}
                    required
                  />
                </div>
              </div>

              <div className="input-group">
                <label className="input-label">Full Name</label>
                <div style={{ position: 'relative' }}>
                  <UserIcon size={16} style={{ position: 'absolute', left: '12px', top: '15px', color: '#64748b' }} />
                  <input
                    type="text"
                    className="input-field"
                    placeholder="John Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    style={{ paddingLeft: '2.5rem', width: '100%' }}
                  />
                </div>
              </div>
            </>
          )}

          <div className="input-group" style={{ marginBottom: '2rem' }}>
            <label className="input-label">Password</label>
            <div style={{ position: 'relative' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '15px', color: '#64748b' }} />
              <input
                type="password"
                className="input-field"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: '2.5rem', width: '100%' }}
                required
              />
            </div>
          </div>

          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '1rem' }} disabled={loading}>
            {loading ? 'Please wait...' : isLogin ? 'Sign In' : 'Sign Up'}
          </button>
        </form>

        <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
          <span 
            style={{ color: '#6366f1', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 600 }}
            onClick={() => { setIsLogin(!isLogin); setError(''); }}
          >
            {isLogin ? "Don't have an account? Sign Up" : 'Already have an account? Log In'}
          </span>
          <br />
          {isLogin && (
            <span style={{ fontSize: '0.8rem', color: '#64748b', display: 'inline-block', marginTop: '1rem' }}>
              Tip: Log in with username <strong>demo</strong> / password <strong>password123</strong>
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
