import React, { useState, useEffect } from 'react';
import {
  BrainCircuit, Activity, Heart, Award, Calendar, CheckCircle2,
  ChevronRight, Flame, BarChart2, TrendingUp, Users, Zap
} from 'lucide-react';

// ── Helper: classification → badge class ─────────────────────────────────────
function badgeClass(c) {
  if (c === 'Healthy')         return 'badge-healthy';
  if (c === 'Mild Stress')     return 'badge-mild';
  if (c === 'Moderate Stress') return 'badge-moderate';
  if (c === 'High Stress')     return 'badge-high';
  if (c === 'Anxiety Risk')    return 'badge-anxiety';
  if (c === 'Depression Risk') return 'badge-depression';
  return '';
}

// ── Helper: emotion → chip class ─────────────────────────────────────────────
function emotionChipClass(e) {
  const map = {
    Happy: 'emotion-happy', Sad: 'emotion-sad', Angry: 'emotion-angry',
    Fear: 'emotion-fear', Surprise: 'emotion-surprise', Disgust: 'emotion-disgust',
    Neutral: 'emotion-neutral', Calm: 'emotion-calm',
  };
  return map[e] || 'emotion-neutral';
}

// ── Radar Chart (SVG) ─────────────────────────────────────────────────────────
function RadarChart({ data }) {
  // data: [{label, value (0-100)}, ...]
  const cx = 140, cy = 140, r = 100;
  const n = data.length;
  const angleStep = (2 * Math.PI) / n;

  const polarToXY = (angle, radius) => ({
    x: cx + radius * Math.sin(angle),
    y: cy - radius * Math.cos(angle),
  });

  // Grid rings
  const rings = [25, 50, 75, 100];

  // Axis lines & labels
  const axes = data.map((d, i) => {
    const angle = i * angleStep;
    const outer = polarToXY(angle, r);
    const labelPos = polarToXY(angle, r + 22);
    return { ...d, angle, outer, labelPos };
  });

  // Data polygon
  const points = data.map((d, i) => {
    const angle = i * angleStep;
    return polarToXY(angle, (d.value / 100) * r);
  });
  const polyStr = points.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <svg viewBox="0 0 280 280" className="chart-svg" style={{ maxWidth: 280 }}>
      {/* Grid rings */}
      {rings.map(pct => {
        const ringPts = data.map((_, i) => polarToXY(i * angleStep, (pct / 100) * r));
        const ringStr = ringPts.map(p => `${p.x},${p.y}`).join(' ');
        return (
          <polygon
            key={pct}
            points={ringStr}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        );
      })}

      {/* Axis lines */}
      {axes.map((ax, i) => (
        <line key={i} x1={cx} y1={cy} x2={ax.outer.x} y2={ax.outer.y}
          stroke="rgba(255,255,255,0.08)" strokeWidth="1" />
      ))}

      {/* Data fill */}
      <polygon points={polyStr}
        fill="rgba(99,102,241,0.18)"
        stroke="var(--color-primary)"
        strokeWidth="2"
        strokeLinejoin="round"
      />

      {/* Data dots */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="4"
          fill="var(--color-secondary)" stroke="none" />
      ))}

      {/* Labels */}
      {axes.map((ax, i) => (
        <text key={i} x={ax.labelPos.x} y={ax.labelPos.y}
          fill="#94a3b8" fontSize="9.5" textAnchor="middle"
          dominantBaseline="middle" fontWeight="600">
          {ax.label}
        </text>
      ))}

      {/* Center dot */}
      <circle cx={cx} cy={cy} r="3" fill="rgba(255,255,255,0.2)" />
    </svg>
  );
}

// ── SVG Trend Line Chart ──────────────────────────────────────────────────────
function TrendChart({ history }) {
  if (!history || history.length < 2) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#64748b', fontSize: '0.85rem' }}>
      Complete more assessments to see your wellness trend.
    </div>
  );

  const W = 580, H = 170, PX = 32, PY = 20;
  const cw = W - PX * 2, ch = H - PY * 2;

  const pts = history.map((h, i) => ({
    x: PX + (i / (history.length - 1)) * cw,
    y: PY + (1 - h.score / 100) * ch,
    ...h,
  }));

  const linePath = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const fillPath = `${linePath} L ${pts[pts.length - 1].x} ${H - PY} L ${pts[0].x} ${H - PY} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart-svg">
      <defs>
        <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.0" />
        </linearGradient>
      </defs>
      {/* Y-axis grid */}
      {[25, 50, 75, 100].map(v => {
        const y = PY + (1 - v / 100) * ch;
        return (
          <g key={v}>
            <line x1={PX} y1={y} x2={W - PX} y2={y} stroke="rgba(255,255,255,0.04)" />
            <text x={PX - 6} y={y + 4} fill="#475569" fontSize="9" textAnchor="end">{v}</text>
          </g>
        );
      })}
      {/* Fill area */}
      <path d={fillPath} fill="url(#trendGrad)" />
      {/* Line */}
      <path d={linePath} fill="none" stroke="var(--color-primary)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      {/* Points */}
      {pts.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r="5" fill="var(--color-secondary)" />
          <circle cx={p.x} cy={p.y} r="9" fill="none" stroke="var(--color-secondary)" strokeWidth="1.5" opacity="0.35" />
          <text x={p.x} y={p.y - 13} fill="#fff" fontSize="9.5" textAnchor="middle" fontWeight="700">
            {Math.round(p.score)}
          </text>
          {i === 0 || i === pts.length - 1 ? (
            <text x={p.x} y={H - 4} fill="#475569" fontSize="8.5" textAnchor="middle">{p.date}</text>
          ) : null}
        </g>
      ))}
    </svg>
  );
}

// ── Modality Breakdown Bar ────────────────────────────────────────────────────
function ModalityBreakdown({ data }) {
  if (!data || data.length === 0) return null;
  const colours = { Questionnaire: 'modality-q', Facial: 'modality-face', Speech: 'modality-speech' };
  const icons = { Questionnaire: '📋', Facial: '👁️', Speech: '🎙️' };
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      {data.map(m => (
        <div key={m.modality}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.83rem', marginBottom: '0.3rem' }}>
            <span style={{ color: '#cbd5e1' }}>{icons[m.modality] || ''} {m.modality}</span>
            <span style={{ color: '#64748b', fontWeight: 700 }}>{m.weight_pct}%</span>
          </div>
          <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
            <div
              className={`modality-bar ${colours[m.modality] || 'modality-q'}`}
              style={{ width: `${m.weight_pct}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── SHAP Attribution Display ──────────────────────────────────────────────────
function SHAPChart({ shapValues }) {
  if (!shapValues || Object.keys(shapValues).length === 0) return null;
  const maxAbs = Math.max(...Object.values(shapValues).map(Math.abs), 1);
  return (
    <div className="shap-bar-container">
      {Object.entries(shapValues).map(([feat, val]) => {
        const isPos = val >= 0;
        const pct = (Math.abs(val) / maxAbs) * 48; // max half-width = 48%
        return (
          <div key={feat} className="shap-row">
            <div className="shap-label-row">
              <span style={{ color: '#cbd5e1', fontWeight: 500, fontSize: '0.83rem' }}>{feat}</span>
              <span style={{ color: isPos ? '#34d399' : '#f87171', fontWeight: 700, fontSize: '0.83rem' }}>
                {isPos ? '+' : ''}{val.toFixed(1)} pts
              </span>
            </div>
            <div className="shap-bar-track">
              <div className="shap-bar-midline" />
              <div
                className="shap-bar-fill"
                style={{
                  width: `${pct}%`,
                  left: isPos ? '50%' : 'auto',
                  right: !isPos ? '50%' : 'auto',
                  background: isPos ? 'var(--color-success)' : 'var(--color-danger)',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Emotion Timeline ──────────────────────────────────────────────────────────
function EmotionTimeline({ timeline }) {
  if (!timeline || timeline.length === 0) return (
    <div style={{ color: '#64748b', fontSize: '0.85rem', textAlign: 'center', padding: '1rem' }}>
      No emotion data yet. Complete an assessment.
    </div>
  );
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', maxHeight: '280px', overflowY: 'auto' }}>
      {timeline.map((t, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '0.6rem 0.85rem',
          background: 'rgba(255,255,255,0.025)',
          borderRadius: '10px',
          border: '1px solid rgba(255,255,255,0.04)',
          gap: '0.75rem',
        }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', flex: 1 }}>
            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{t.date}</span>
            <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
              {t.facial_emotion && t.facial_emotion !== 'N/A' && (
                <span className={`emotion-chip ${emotionChipClass(t.facial_emotion)}`}>
                  👁 {t.facial_emotion}
                </span>
              )}
              {t.speech_emotion && t.speech_emotion !== 'N/A' && (
                <span className={`emotion-chip ${emotionChipClass(t.speech_emotion)}`}>
                  🎙 {t.speech_emotion}
                </span>
              )}
            </div>
          </div>
          {t.fused_score && (
            <div style={{ textAlign: 'right', flexShrink: 0 }}>
              <div style={{ fontSize: '1.3rem', fontWeight: 800, color: '#fff' }}>
                {Math.round(t.fused_score)}
              </div>
              {t.classification && (
                <span className={`classification-badge ${badgeClass(t.classification)}`} style={{ fontSize: '0.68rem', padding: '2px 7px' }}>
                  {t.classification}
                </span>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}


// ── Main Dashboard Component ──────────────────────────────────────────────────
export default function MentalHealthDashboard({ token, API_BASE_URL, currentUser, setActiveTab }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { fetchDashboard(); }, []);

  const fetchDashboard = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/dashboard/summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setData(await res.json());
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px', gap: '1rem', flexDirection: 'column' }}>
      <div className="spinner" />
      <span style={{ color: '#64748b', fontSize: '0.9rem' }}>Loading analytics...</span>
    </div>
  );

  // ── Welcome / Empty State ──────────────────────────────────────────────────
  if (!data || data.total_assessments === 0) return (
    <div className="animated-view text-center" style={{ maxWidth: 680, margin: '4rem auto' }}>
      <div className="glass-panel" style={{ padding: '3.5rem 2.5rem' }}>
        <div style={{ width: 72, height: 72, margin: '0 auto 1.5rem', borderRadius: 18, background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 8px 32px var(--color-primary-glow)' }}>
          <BrainCircuit size={34} color="#fff" />
        </div>
        <h2 style={{ fontSize: '1.9rem', color: '#fff', marginBottom: '0.75rem' }}>
          Welcome, {currentUser?.full_name?.split(' ')[0] || currentUser?.username}! 👋
        </h2>
        <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: '1.6', marginBottom: '2rem', maxWidth: 480, margin: '0 auto 2rem' }}>
          Your personalised Mental Well-Being dashboard is ready. Complete your first multimodal assessment — involving a brief questionnaire, optional webcam capture, and voice recording — to unlock your wellness score and AI-driven insights.
        </p>
        <button onClick={() => setActiveTab('assessment')} className="btn btn-primary" style={{ fontSize: '1rem', padding: '0.9rem 2rem' }}>
          <Activity size={18} />
          <span>Start First Assessment</span>
          <ChevronRight size={16} />
        </button>
        <p style={{ color: '#475569', fontSize: '0.75rem', marginTop: '1.25rem', lineHeight: '1.4' }}>
          ⚠️ This tool is for educational purposes only. Not a medical service.
        </p>
      </div>
    </div>
  );

  const last = data.last_assessment;
  let shapValues = {};
  let xaiData = {};
  let recs = {};
  try { xaiData = JSON.parse(last.explainability_data); shapValues = xaiData.shap_values || {}; } catch {}
  try { recs = JSON.parse(last.recommendations); } catch {}

  const radarData = [
    { label: 'PHQ-9',   value: last.questionnaire_score ? Math.max(0, 100 - (last.questionnaire_score > 50 ? 100 - last.questionnaire_score : last.questionnaire_score)) : 60 },
    { label: 'GAD-7',   value: last.questionnaire_score ? last.questionnaire_score : 60 },
    { label: 'Wellness', value: last.fused_score },
    { label: 'Facial',  value: last.facial_score ?? last.fused_score },
    { label: 'Voice',   value: last.speech_score ?? last.fused_score },
    { label: 'WHO-5',   value: last.questionnaire_score ? Math.min(100, last.questionnaire_score + 10) : 65 },
  ];

  return (
    <div className="animated-view">
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.75rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.3rem' }}>Mental Well-Being Index</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
            Multimodal AI analysis · {data.total_assessments} session{data.total_assessments > 1 ? 's' : ''} recorded
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap', alignItems: 'center' }}>
          {data.current_streak > 0 && (
            <div className="streak-badge">
              <Flame size={14} />
              {data.current_streak} day streak
            </div>
          )}
          <button onClick={() => setActiveTab('assessment')} className="btn btn-primary">
            <Activity size={16} />
            New Assessment
          </button>
        </div>
      </div>

      {/* Top Metrics Row */}
      <div className="dashboard-grid stagger-children" style={{ marginBottom: '1.5rem' }}>
        {/* Fused Score */}
        <div className="glass-panel metric-card">
          <div style={{ position: 'absolute', width: 80, height: 80, background: last.classification === 'Healthy' ? 'var(--color-success-glow)' : 'var(--color-primary-glow)', filter: 'blur(24px)', top: -20, right: -20, borderRadius: '50%' }} />
          <div className="metric-label">Fused Well-Being Score</div>
          <div className="metric-value">{Math.round(last.fused_score)}</div>
          <span className={`classification-badge ${badgeClass(last.classification)}`}>
            {last.classification}
          </span>
          <div className="metric-sub">Confidence: {Math.round(last.confidence * 100)}%</div>
        </div>

        {/* Weekly / Monthly */}
        <div className="glass-panel metric-card">
          <div className="metric-label">Period Averages</div>
          <div style={{ display: 'flex', justifyContent: 'space-around', margin: '1rem 0' }}>
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '0.2rem' }}>7-Day</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff' }}>{Math.round(data.weekly_average)}</div>
            </div>
            <div style={{ width: 1, background: 'rgba(255,255,255,0.05)' }} />
            <div>
              <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '0.2rem' }}>30-Day</div>
              <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fff' }}>{Math.round(data.monthly_average)}</div>
            </div>
          </div>
          <div className="metric-sub">{data.total_assessments} total sessions</div>
        </div>

        {/* Streak */}
        <div className="glass-panel metric-card">
          <div className="metric-label">Streak & Progress</div>
          <div className="metric-value" style={{ fontSize: '2.5rem', color: '#fbbf24' }}>
            {data.current_streak > 0 ? `🔥 ${data.current_streak}` : '—'}
          </div>
          <div className="metric-sub">Best: {data.longest_streak} days</div>
        </div>
      </div>

      {/* Main Analytics Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* Left Column: Trend + SHAP */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Wellness Progress Trend */}
          <div className="glass-panel" style={{ marginBottom: 0 }}>
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <TrendingUp size={17} color="#6366f1" /> Wellness Progress Trend
            </h3>
            <div className="chart-container">
              <TrendChart history={data.score_history} />
            </div>
          </div>

          {/* SHAP Attributions */}
          <div className="glass-panel" style={{ marginBottom: 0 }}>
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={17} color="#06b6d4" /> Explainable AI – Feature Attributions
            </h3>
            <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '1rem', lineHeight: '1.4' }}>
              How each feature pushed your score above or below the {xaiData.baseline_score || 80}-point healthy baseline.
            </p>
            <SHAPChart shapValues={shapValues} />
          </div>
        </div>

        {/* Right Column: Radar + Modality + Emotions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Wellness Radar */}
          <div className="glass-panel" style={{ marginBottom: 0 }}>
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart2 size={17} color="#d946ef" /> Dimension Radar
            </h3>
            <div className="radar-container">
              <RadarChart data={radarData} />
            </div>
          </div>

          {/* Modality Breakdown */}
          <div className="glass-panel" style={{ marginBottom: 0 }}>
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={17} color="#06b6d4" /> Modality Contributions
            </h3>
            <ModalityBreakdown data={data.modality_breakdown} />
          </div>

          {/* Emotion Timeline */}
          <div className="glass-panel" style={{ marginBottom: 0 }}>
            <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Calendar size={17} color="#a855f7" /> Emotion Timeline
            </h3>
            <EmotionTimeline timeline={data.emotion_timeline} />
          </div>
        </div>
      </div>

      {/* Recommendations */}
      {recs && Object.keys(recs).length > 0 && (
        <div className="glass-panel">
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Heart size={17} color="#d946ef" /> Personalised Wellness Recommendations
          </h3>

          {/* Professional Help Alert */}
          {recs.professional_help?.triggered && (
            <div className="pro-help-card">
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ef4444' }}>⚠️ Professional Support Advised</span>
              </div>
              <p style={{ fontSize: '0.8rem', color: '#f87171', lineHeight: '1.4', marginBottom: '0.75rem' }}>
                {recs.professional_help.reason}
              </p>
              {recs.professional_help.resources?.slice(0, 3).map((r, i) => (
                <div key={i} className="pro-help-resource">
                  <strong>{r.name}</strong>: {r.contact}
                  <span style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.1rem' }}>{r.description}</span>
                </div>
              ))}
            </div>
          )}

          {/* Affirmations */}
          {recs.affirmations?.length > 0 && (
            <div className="affirmation-card" style={{ marginBottom: '1.25rem' }}>
              {recs.affirmations[0]}
            </div>
          )}

          {/* Rec categories grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1.25rem' }}>
            {[
              { key: 'breathing',  label: 'Breathing Techniques', color: '#818cf8' },
              { key: 'mindfulness',label: 'Mindfulness',          color: '#06b6d4' },
              { key: 'journaling', label: 'Journaling Prompts',   color: '#d946ef' },
              { key: 'music',      label: 'Music Therapy',        color: '#a855f7' },
              { key: 'sleep',      label: 'Sleep Hygiene',        color: '#22d3ee' },
              { key: 'exercise',   label: 'Exercise Plan',        color: '#34d399' },
            ].filter(cat => recs[cat.key]?.length > 0).map(cat => (
              <div key={cat.key}>
                <div className="rec-category-header" style={{ color: cat.color }}>
                  {cat.label}
                </div>
                {recs[cat.key].map((item, j) => (
                  <div key={j} className="rec-item">
                    <CheckCircle2 size={12} color="var(--color-secondary)" style={{ flexShrink: 0, display: 'inline', marginRight: 6, verticalAlign: 'middle' }} />
                    <span dangerouslySetInnerHTML={{ __html: item.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Weekly Plan */}
          {recs.weekly_plan?.length > 0 && (
            <div style={{ marginTop: '1.5rem' }}>
              <h4 style={{ fontSize: '0.9rem', color: '#fff', marginBottom: '0.85rem' }}>📅 Your 7-Day Wellness Plan</h4>
              <div className="weekly-plan-grid">
                {recs.weekly_plan.map((day, i) => (
                  <div key={i} className="plan-day-card">
                    <div className="plan-day-label">{day.day}</div>
                    {day.activities.map((act, j) => (
                      <div key={j} className="plan-activity">{act}</div>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
