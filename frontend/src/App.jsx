import React, { useState, useEffect, useCallback } from 'react';
import { registerToastHandler, showToast } from './toast';
import {
  LayoutDashboard, Activity, MessageSquare, User, LogOut,
  BrainCircuit, Menu, X, FileText, Flame, ChevronRight
} from 'lucide-react';
import Auth from './components/Auth';
import MentalHealthDashboard from './components/MentalHealthDashboard';
import Questionnaire from './components/Questionnaire';
import Chatbot from './components/Chatbot';
import Profile from './components/Profile';
import AssessmentResult from './components/AssessmentResult';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

// ── Toast System ──────────────────────────────────────────────────────────────

function ToastContainer() {
  const [toasts, setToasts] = useState([]);
  registerToastHandler((message, type) => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500);
  });
  if (!toasts.length) return null;
  return (
    <div className="toast-container">
      {toasts.map(t => (
        <div key={t.id} className={`toast ${t.type}`}>
          {t.type === 'success' && '✓ '}
          {t.type === 'error' && '⚠ '}
          {t.type === 'info' && '● '}
          {t.message}
        </div>
      ))}
    </div>
  );
}

// ── Nav Items Config ──────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'assessment', label: 'New Assessment', icon: Activity },
  { id: 'chatbot', label: 'Wellness Chat', icon: MessageSquare },
  { id: 'reports', label: 'Reports', icon: FileText },
  { id: 'profile', label: 'Profile & History', icon: User },
];

// ── Classification Badge Helper ───────────────────────────────────────────────
function getClassBadgeClass(c) {
  if (!c) return '';
  if (c === 'Healthy') return 'badge-healthy';
  if (c === 'Mild Stress') return 'badge-mild';
  if (c === 'Moderate Stress') return 'badge-moderate';
  if (c === 'High Stress') return 'badge-high';
  if (c === 'Anxiety Risk') return 'badge-anxiety';
  if (c === 'Depression Risk') return 'badge-depression';
  return '';
}

// ── Reports Page (inline lightweight) ────────────────────────────────────────
function ReportsPage({ token, API_BASE_URL }) {
  const [weekly, setWeekly] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [allTime, setAllTime] = useState(null);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState('weekly');

  useEffect(() => {
    const headers = { Authorization: `Bearer ${token}` };
    Promise.all([
      fetch(`${API_BASE_URL}/reports/weekly`, { headers }).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/reports/monthly`, { headers }).then(r => r.ok ? r.json() : null),
      fetch(`${API_BASE_URL}/reports/all-time`, { headers }).then(r => r.ok ? r.json() : null),
    ]).then(([w, m, a]) => {
      setWeekly(w); setMonthly(m); setAllTime(a);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '300px' }}>
      <div className="spinner" />
    </div>
  );

  const data = tab === 'weekly' ? weekly : tab === 'monthly' ? monthly : allTime;

  return (
    <div className="animated-view">
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>Wellness Reports</h1>
      <p style={{ color: '#94a3b8', marginBottom: '1.5rem' }}>Longitudinal mental health analytics and trend insights</p>

      {/* Tab switcher */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {['weekly', 'monthly', 'all-time'].map(t => (
          <button key={t} className={`btn ${tab === t ? 'btn-primary' : 'btn-secondary'}`}
            style={{ textTransform: 'capitalize', fontSize: '0.85rem', padding: '0.55rem 1.1rem' }}
            onClick={() => setTab(t)}>
            {t}
          </button>
        ))}
      </div>

      {!data || data.total_assessments === 0 ? (
        <div className="glass-panel text-center" style={{ padding: '3rem' }}>
          <FileText size={48} color="#6366f1" style={{ marginBottom: '1rem', opacity: 0.6 }} />
          <h3 style={{ color: '#fff', marginBottom: '0.5rem' }}>No data yet</h3>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Complete assessments to see your reports.</p>
        </div>
      ) : (
        <div className="stagger-children" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.25rem', marginBottom: '1.5rem' }}>
          {[
            { label: 'Total Sessions', value: data.total_assessments, color: '#818cf8' },
            { label: 'Average Score', value: data.average_score ?? data.lifetime_average, color: '#34d399' },
            { label: 'Best Score', value: data.best_score ?? data.all_time_best, color: '#22d3ee' },
            { label: 'Trend', value: data.trend ?? 'N/A', color: '#fbbf24', isText: true },
          ].map((m, i) => (
            <div key={i} className="glass-panel metric-card">
              <div className="metric-label">{m.label}</div>
              <div className="metric-value" style={{ color: m.color, fontSize: m.isText ? '1.3rem' : '2.5rem' }}>{m.value}</div>
            </div>
          ))}
        </div>
      )}

      {data?.classification_distribution && (
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.05rem', color: '#fff', marginBottom: '1.25rem' }}>Classification Distribution</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {Object.entries(data.classification_distribution).map(([cls, count]) => {
              const total = data.total_assessments;
              const pct = Math.round((count / total) * 100);
              return (
                <div key={cls}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.3rem' }}>
                    <span className={`classification-badge ${getClassBadgeClass(cls)}`}>{cls}</span>
                    <span style={{ color: '#64748b' }}>{count} ({pct}%)</span>
                  </div>
                  <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                    <div style={{ width: `${pct}%`, height: '100%', background: 'var(--color-primary)', borderRadius: '3px', transition: 'width 0.6s ease' }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {data?.daily_breakdown?.length > 0 && (
        <div className="glass-panel">
          <h3 style={{ fontSize: '1.05rem', color: '#fff', marginBottom: '1.25rem' }}>Daily Breakdown</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.daily_breakdown.map((d, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0.75rem', background: 'rgba(255,255,255,0.025)', borderRadius: '10px' }}>
                <span style={{ color: '#94a3b8', fontSize: '0.88rem' }}>{d.day}</span>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{d.sessions} session{d.sessions > 1 ? 's' : ''}</span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700, color: '#fff' }}>{d.avg_score}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'all-time' && allTime?.current_streak > 0 && (
        <div className="glass-panel" style={{ display: 'flex', gap: '2rem', alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div className="streak-badge" style={{ fontSize: '1.5rem', padding: '0.6rem 1.2rem' }}>
              🔥 {allTime.current_streak}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.35rem' }}>Current Streak</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fbbf24' }}>{allTime.longest_streak}</div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Longest Streak</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>First Assessment</div>
            <div style={{ fontSize: '0.95rem', color: '#fff', fontWeight: 600 }}>{allTime.first_assessment}</div>
          </div>
        </div>
      )}
    </div>
  );
}


// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [currentUser, setCurrentUser] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // For the assessment result full-screen view
  const [assessmentResult, setAssessmentResult] = useState(null);

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      fetchCurrentUser();
    } else {
      localStorage.removeItem('token');
      setCurrentUser(null);
    }
  }, [token]);

  const fetchCurrentUser = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setCurrentUser(await res.json());
      else setToken('');
    } catch { setToken(''); }
    finally { setLoading(false); }
  };

  const handleLogout = () => {
    setToken(''); setCurrentUser(null);
    setActiveTab('dashboard'); setAssessmentResult(null);
  };

  const handleAssessmentComplete = (result) => {
    setAssessmentResult(result);
    setActiveTab('result');
  };

  if (!token) return <Auth setToken={setToken} API_BASE_URL={API_BASE_URL} />;

  if (loading && !currentUser) return (
    <div style={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#070810', flexDirection: 'column', gap: '1.25rem' }}>
      <div className="logo-icon" style={{ width: 56, height: 56, borderRadius: 14 }}>
        <BrainCircuit size={28} color="#fff" />
      </div>
      <div className="spinner" />
      <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading Talk2Mind...</p>
    </div>
  );

  return (
    <div className="app-container">
      <ToastContainer />

      {/* Mobile Top Bar */}
      <div className="mobile-topbar">
        <button className="hamburger-btn" onClick={() => setMobileMenuOpen(true)}>
          <Menu size={22} />
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div className="logo-icon" style={{ width: 28, height: 28, borderRadius: 8 }}>
            <BrainCircuit size={14} color="#fff" />
          </div>
          <span style={{ fontWeight: 700, fontSize: '1rem', fontFamily: 'var(--font-heading)' }}>Talk2Mind</span>
        </div>
        <div style={{ width: 28 }} />
      </div>

      {/* Sidebar Overlay (mobile) */}
      <div
        className={`sidebar-overlay ${mobileMenuOpen ? 'open' : ''}`}
        onClick={() => setMobileMenuOpen(false)}
      />

      {/* Sidebar */}
      <nav className={`sidebar ${mobileMenuOpen ? 'open' : ''}`}>
        <div className="logo-container">
          <div className="logo-icon">
            <BrainCircuit size={20} color="#fff" />
          </div>
          <span className="logo-text">Talk2Mind</span>
        </div>

        <ul className="nav-links">
          {NAV_ITEMS.map(item => (
            <li key={item.id}>
              <div
                className={`nav-item ${activeTab === item.id || (activeTab === 'result' && item.id === 'assessment') ? 'active' : ''}`}
                onClick={() => { setActiveTab(item.id); setMobileMenuOpen(false); }}
              >
                <item.icon size={18} />
                <span>{item.label}</span>
              </div>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          {currentUser && (
            <div className="user-profile-badge">
              <div className="user-avatar">
                {(currentUser.full_name || currentUser.username)[0].toUpperCase()}
              </div>
              <div style={{ flexGrow: 1, overflow: 'hidden' }}>
                <h4 style={{ fontSize: '0.88rem', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {currentUser.full_name || currentUser.username}
                </h4>
                <p style={{ fontSize: '0.72rem', color: '#64748b' }}>Wellness Journey</p>
              </div>
            </div>
          )}
          <div
            className="nav-item"
            onClick={handleLogout}
            style={{ color: '#f87171' }}
          >
            <LogOut size={17} />
            <span>Sign Out</span>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content animated-view">
        {activeTab === 'dashboard' && (
          <MentalHealthDashboard
            token={token}
            API_BASE_URL={API_BASE_URL}
            currentUser={currentUser}
            setActiveTab={setActiveTab}
          />
        )}
        {(activeTab === 'assessment' || activeTab === 'result') && !assessmentResult && (
          <Questionnaire
            token={token}
            API_BASE_URL={API_BASE_URL}
            setActiveTab={setActiveTab}
            onComplete={handleAssessmentComplete}
          />
        )}
        {activeTab === 'result' && assessmentResult && (
          <AssessmentResult
            result={assessmentResult}
            onDashboard={() => { setAssessmentResult(null); setActiveTab('dashboard'); }}
            onNewAssessment={() => { setAssessmentResult(null); setActiveTab('assessment'); }}
          />
        )}
        {activeTab === 'chatbot' && (
          <Chatbot token={token} API_BASE_URL={API_BASE_URL} />
        )}
        {activeTab === 'reports' && (
          <ReportsPage token={token} API_BASE_URL={API_BASE_URL} />
        )}
        {activeTab === 'profile' && (
          <Profile
            token={token}
            API_BASE_URL={API_BASE_URL}
            currentUser={currentUser}
            setCurrentUser={setCurrentUser}
          />
        )}
      </main>
    </div>
  );
}
