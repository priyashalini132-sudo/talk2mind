import React, { useState, useEffect } from 'react';
import { User, Mail, ShieldAlert, Award, Calendar } from 'lucide-react';

export default function Profile({ token, API_BASE_URL, currentUser, setCurrentUser }) {
  const [history, setHistory] = useState([]);
  const [email, setEmail] = useState(currentUser?.email || '');
  const [fullName, setFullName] = useState(currentUser?.full_name || '');
  const [password, setPassword] = useState('');
  const [updateMsg, setUpdateMsg] = useState({ type: '', text: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/dashboard/summary`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.score_history || []);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setUpdateMsg({ type: '', text: '' });
    setLoading(true);

    try {
      const body = { email, full_name: fullName };
      if (password) body.password = password;

      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(body)
      });

      const data = await res.json();
      if (res.ok) {
        setUpdateMsg({ type: 'success', text: 'Profile updated successfully!' });
        setCurrentUser(data);
        setPassword('');
      } else {
        setUpdateMsg({ type: 'error', text: data.detail || 'Failed to update profile.' });
      }
    } catch (err) {
      setUpdateMsg({ type: 'error', text: 'Connection error.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animated-view">
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2.25rem', marginBottom: '0.5rem', color: '#fff' }}>Profile & Diagnostics Log</h1>
        <p style={{ color: '#94a3b8' }}>Manage profile settings and view your historical assessment records</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 2fr', gap: '2rem' }}>
        
        {/* Left Column: Profile Settings */}
        <div>
          <div className="glass-panel">
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fff' }}>
              <User size={18} color="#6366f1" /> Account Settings
            </h3>

            {updateMsg.text && (
              <div style={{
                background: updateMsg.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                border: updateMsg.type === 'success' ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '10px',
                padding: '0.8rem',
                color: updateMsg.type === 'success' ? '#34d399' : '#f87171',
                fontSize: '0.85rem',
                marginBottom: '1.5rem',
                textAlign: 'center'
              }}>
                {updateMsg.text}
              </div>
            )}

            <form onSubmit={handleUpdateProfile}>
              <div className="input-group">
                <label className="input-label">Full Name</label>
                <input
                  type="text"
                  className="input-field"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

              <div className="input-group">
                <label className="input-label">Email Address</label>
                <input
                  type="email"
                  className="input-field"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="input-group" style={{ marginBottom: '1.5rem' }}>
                <label className="input-label">Update Password (Leave blank to keep current)</label>
                <input
                  type="password"
                  className="input-field"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
                {loading ? 'Saving...' : 'Update Settings'}
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Historical Log */}
        <div>
          <div className="glass-panel" style={{ minHeight: '400px' }}>
            <h3 style={{ fontSize: '1.2rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#fff' }}>
              <Calendar size={18} color="#06b6d4" /> Diagnostic Session Log
            </h3>

            {history.length === 0 ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '250px',
                color: '#64748b',
                textAlign: 'center'
              }}>
                <ShieldAlert size={36} style={{ marginBottom: '1rem', color: '#f59e0b' }} />
                <p>No screening sessions logged yet.</p>
                <p style={{ fontSize: '0.85rem', marginTop: '0.5rem' }}>Complete a wellness assessment to log your first results.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '500px', overflowY: 'auto', paddingRight: '5px' }}>
                {history.map((h, idx) => (
                  <div 
                    key={idx} 
                    style={{
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid rgba(255, 255, 255, 0.05)',
                      borderRadius: '12px',
                      padding: '1.2rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.25)';
                      e.currentTarget.style.background = 'rgba(99, 102, 241, 0.02)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.05)';
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.02)';
                    }}
                  >
                    <div>
                      <h4 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.25rem' }}>
                        Assessment Session #{history.length - idx}
                      </h4>
                      <p style={{ fontSize: '0.8rem', color: '#64748b' }}>{h.date}</p>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          background: h.classification === 'Healthy' ? 'rgba(16, 185, 129, 0.15)' : 
                                      h.classification.includes('Stress') ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                          color: h.classification === 'Healthy' ? '#34d399' :
                                 h.classification.includes('Stress') ? '#fbbf24' : '#f87171',
                        }}>
                          {h.classification}
                        </span>
                      </div>
                      
                      <div style={{
                        width: '45px',
                        height: '45px',
                        borderRadius: '50%',
                        background: 'rgba(99, 102, 241, 0.1)',
                        border: '1px solid rgba(99, 102, 241, 0.3)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontWeight: 700,
                        color: '#818cf8',
                        fontSize: '1rem'
                      }}>
                        {Math.round(h.score)}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
