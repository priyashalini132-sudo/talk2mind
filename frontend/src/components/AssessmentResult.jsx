import React, { useState, useEffect, useRef } from 'react';
import {
  CheckCircle2, Heart, ShieldAlert, BarChart2, BrainCircuit,
  Activity, Flame, Download, RefreshCw, ChevronRight, Zap
} from 'lucide-react';

// ── Score circle helpers ───────────────────────────────────────────────────────
function scoreCircleClass(classification) {
  const map = {
    'Healthy':          'score-circle-healthy',
    'Mild Stress':      'score-circle-mild',
    'Moderate Stress':  'score-circle-moderate',
    'High Stress':      'score-circle-high',
    'Anxiety Risk':     'score-circle-anxiety',
    'Depression Risk':  'score-circle-depression',
  };
  return map[classification] || 'score-circle-mild';
}
function badgeClass(c) {
  const m = { 'Healthy': 'badge-healthy', 'Mild Stress': 'badge-mild', 'Moderate Stress': 'badge-moderate', 'High Stress': 'badge-high', 'Anxiety Risk': 'badge-anxiety', 'Depression Risk': 'badge-depression' };
  return m[c] || '';
}

// ── Animated counter ─────────────────────────────────────────────────────────
function AnimatedScore({ target }) {
  const [current, setCurrent] = useState(0);
  useEffect(() => {
    let start = 0;
    const end = Math.round(target);
    if (start === end) return;
    const step = Math.max(1, Math.floor(end / 40));
    const timer = setInterval(() => {
      start = Math.min(start + step, end);
      setCurrent(start);
      if (start >= end) clearInterval(timer);
    }, 25);
    return () => clearInterval(timer);
  }, [target]);
  return <>{current}</>;
}

// ── Mini SHAP Bar (for result page) ──────────────────────────────────────────
function MiniSHAPChart({ shapValues }) {
  if (!shapValues || !Object.keys(shapValues).length) return null;
  const maxAbs = Math.max(...Object.values(shapValues).map(Math.abs), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
      {Object.entries(shapValues).map(([feat, val]) => {
        const isPos = val >= 0;
        const pct = (Math.abs(val) / maxAbs) * 45;
        return (
          <div key={feat}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
              <span style={{ color: '#cbd5e1' }}>{feat}</span>
              <span style={{ color: isPos ? '#34d399' : '#f87171', fontWeight: 700 }}>
                {isPos ? '+' : ''}{val.toFixed(1)} pts
              </span>
            </div>
            <div style={{ height: '7px', background: 'rgba(255,255,255,0.04)', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
              <div style={{ position: 'absolute', left: '50%', width: 1, background: 'rgba(255,255,255,0.12)', height: '100%' }} />
              <div style={{
                position: 'absolute',
                left: isPos ? '50%' : 'auto',
                right: !isPos ? '50%' : 'auto',
                width: `${pct}%`,
                height: '100%',
                borderRadius: '4px',
                background: isPos ? 'var(--color-success)' : 'var(--color-danger)',
                transition: 'width 0.6s ease',
              }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Subscale Score Bar ────────────────────────────────────────────────────────
function ScoreBar({ label, value, max, color }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div style={{ marginBottom: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.3rem' }}>
        <span style={{ color: '#94a3b8' }}>{label}</span>
        <span style={{ color: '#fff', fontWeight: 700 }}>{value} / {max}</span>
      </div>
      <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ width: `${pct}%`, height: '100%', background: color, borderRadius: '3px', transition: 'width 0.6s ease' }} />
      </div>
    </div>
  );
}

// ── Main Result Component ─────────────────────────────────────────────────────
export default function AssessmentResult({ result, onDashboard, onNewAssessment }) {
  const [showAll, setShowAll] = useState(false);

  if (!result) return null;

  let xaiData = {}, shapValues = {}, modality = [], narrative = '', featureRanking = [];
  let recs = {}, recommendations = {};
  try { xaiData = JSON.parse(result.explainability_data); } catch {}
  try { recs = JSON.parse(result.recommendations); } catch {}

  shapValues    = xaiData.shap_values || {};
  modality      = xaiData.modality_weights || {};
  narrative     = xaiData.narrative || '';
  featureRanking = xaiData.feature_ranking || [];

  const classification = result.classification;
  const circleClass = scoreCircleClass(classification);

  const scoreColor = {
    'Healthy': '#34d399', 'Mild Stress': '#fbbf24', 'Moderate Stress': '#fb923c',
    'High Stress': '#f87171', 'Anxiety Risk': '#c084fc', 'Depression Risk': '#818cf8',
  }[classification] || '#818cf8';

  return (
    <div className="animated-view">
      {/* Hero Section */}
      <div className="glass-panel" style={{ textAlign: 'center', padding: '2.5rem 2rem', marginBottom: '1.5rem', background: 'linear-gradient(180deg, rgba(14,16,26,0.8), rgba(8,9,18,0.9))' }}>
        <div style={{ marginBottom: '0.75rem' }}>
          <span className="tag" style={{ marginBottom: '1rem', display: 'inline-block' }}>Assessment Complete</span>
          <h1 style={{ fontSize: '1.75rem', color: '#fff', margin: '0.5rem 0' }}>Your Wellness Score</h1>
          <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>Multimodal fusion of questionnaire · facial · voice analysis</p>
        </div>

        {/* Animated Score Circle */}
        <div className={`score-circle ${circleClass}`} style={{ marginBottom: '1.25rem' }}>
          <AnimatedScore target={result.fused_score} />
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <span className={`classification-badge ${badgeClass(classification)}`} style={{ fontSize: '0.92rem', padding: '6px 16px' }}>
            {classification}
          </span>
          <span style={{ fontSize: '0.85rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Activity size={14} />
            Confidence: {Math.round(result.confidence * 100)}%
          </span>
        </div>

        {/* Modality Score Pills */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', flexWrap: 'wrap' }}>
          {result.questionnaire_score !== undefined && (
            <div style={{ fontSize: '0.8rem', padding: '4px 12px', borderRadius: '20px', background: 'rgba(99,102,241,0.12)', border: '1px solid rgba(99,102,241,0.25)', color: '#a5b4fc' }}>
              📋 Questionnaire: {Math.round(result.questionnaire_score)}
            </div>
          )}
          {result.facial_score > 0 && (
            <div style={{ fontSize: '0.8rem', padding: '4px 12px', borderRadius: '20px', background: 'rgba(6,182,212,0.12)', border: '1px solid rgba(6,182,212,0.25)', color: '#22d3ee' }}>
              👁 Facial: {Math.round(result.facial_score)}
            </div>
          )}
          {result.speech_score > 0 && (
            <div style={{ fontSize: '0.8rem', padding: '4px 12px', borderRadius: '20px', background: 'rgba(217,70,239,0.12)', border: '1px solid rgba(217,70,239,0.25)', color: '#e879f9' }}>
              🎙 Speech: {Math.round(result.speech_score)}
            </div>
          )}
        </div>

        {/* CTA Buttons */}
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '1.5rem', flexWrap: 'wrap' }}>
          <button className="btn btn-primary" onClick={onDashboard}>
            <BarChart2 size={16} /> View Full Dashboard
          </button>
          <button className="btn btn-secondary" onClick={onNewAssessment}>
            <RefreshCw size={16} /> New Assessment
          </button>
        </div>
      </div>

      {/* Two-column Analysis */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>

        {/* SHAP Explainability */}
        <div className="glass-panel" style={{ marginBottom: 0 }}>
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Zap size={17} color="#06b6d4" /> AI Explanation (SHAP)
          </h3>
          <p style={{ fontSize: '0.78rem', color: '#64748b', marginBottom: '1rem', lineHeight: '1.4' }}>
            Feature contributions relative to the {xaiData.baseline_score || 80}-point healthy baseline.
          </p>
          <MiniSHAPChart shapValues={shapValues} />
        </div>

        {/* Modality Breakdown */}
        <div className="glass-panel" style={{ marginBottom: 0 }}>
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Activity size={17} color="#d946ef" /> Modality Weight Distribution
          </h3>
          {Object.entries(modality).map(([key, pct]) => {
            const colors = { Questionnaire: '#6366f1', Facial: '#06b6d4', Speech: '#d946ef' };
            return (
              <div key={key} style={{ marginBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', marginBottom: '0.3rem' }}>
                  <span style={{ color: '#94a3b8' }}>{key}</span>
                  <span style={{ color: '#fff', fontWeight: 700 }}>{pct}%</span>
                </div>
                <div style={{ height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${pct}%`, height: '100%', background: colors[key] || '#6366f1', borderRadius: '3px', transition: 'width 0.6s ease' }} />
                </div>
              </div>
            );
          })}

          {/* Feature ranking */}
          {featureRanking.length > 0 && (
            <div style={{ marginTop: '1.25rem' }}>
              <h4 style={{ fontSize: '0.82rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.75rem' }}>Feature Impact Ranking</h4>
              {featureRanking.slice(0, 4).map((f, i) => (
                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.4rem', fontSize: '0.8rem' }}>
                  <span style={{ width: 18, height: 18, borderRadius: '50%', background: 'rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, color: '#94a3b8', flexShrink: 0 }}>{i + 1}</span>
                  <span style={{ color: '#cbd5e1', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{f.feature}</span>
                  <span style={{ color: f.direction === 'positive' ? '#34d399' : '#f87171', fontWeight: 700 }}>
                    {f.direction === 'positive' ? '▲' : '▼'} {f.impact.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* AI Narrative */}
      {narrative && (
        <div className="glass-panel" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <BrainCircuit size={17} color="#6366f1" /> AI Assessment Narrative
          </h3>
          <p style={{ fontSize: '0.88rem', color: '#94a3b8', lineHeight: '1.65' }}>{narrative}</p>
        </div>
      )}

      {/* Professional Help */}
      {recs.professional_help?.triggered && (
        <div className="pro-help-card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', marginBottom: '0.5rem' }}>
            <ShieldAlert size={16} color="#ef4444" />
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: '#ef4444' }}>Professional Support Recommended</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: '#f87171', lineHeight: '1.5', marginBottom: '0.85rem' }}>
            {recs.professional_help.reason}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {recs.professional_help.resources?.map((r, i) => (
              <div key={i} className="pro-help-resource">
                <strong>{r.name}</strong>: {r.contact}
                <span style={{ display: 'block', fontSize: '0.72rem', color: '#94a3b8', marginTop: '0.1rem' }}>{r.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recs && Object.keys(recs).some(k => Array.isArray(recs[k]) && recs[k].length > 0) && (
        <div className="glass-panel" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Heart size={17} color="#d946ef" /> Personalised Recommendations
          </h3>

          {recs.affirmations?.length > 0 && (
            <div className="affirmation-card" style={{ marginBottom: '1.25rem' }}>
              {recs.affirmations[0]}
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
            {[
              { key: 'breathing',   label: 'Breathing',   color: '#818cf8' },
              { key: 'mindfulness', label: 'Mindfulness',  color: '#06b6d4' },
              { key: 'journaling',  label: 'Journaling',   color: '#d946ef' },
              { key: 'music',       label: 'Music Therapy',color: '#a855f7' },
              { key: 'sleep',       label: 'Sleep Hygiene',color: '#22d3ee' },
              { key: 'exercise',    label: 'Exercise',     color: '#34d399' },
            ].filter(cat => recs[cat.key]?.length > 0).map(cat => (
              <div key={cat.key}>
                <div className="rec-category-header" style={{ color: cat.color }}>{cat.label}</div>
                {recs[cat.key].map((item, j) => (
                  <div key={j} className="rec-item">
                    <span dangerouslySetInnerHTML={{ __html: item.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }} />
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weekly Plan */}
      {recs.weekly_plan?.length > 0 && (
        <div className="glass-panel">
          <h3 style={{ fontSize: '1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            📅 Your 7-Day Wellness Plan
          </h3>
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

      {/* Bottom CTAs */}
      <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'center', marginTop: '0.5rem', flexWrap: 'wrap', paddingBottom: '2rem' }}>
        <button className="btn btn-primary" onClick={onDashboard}>
          <BarChart2 size={16} /> Go to Dashboard
        </button>
        <button className="btn btn-secondary" onClick={onNewAssessment}>
          <RefreshCw size={16} /> Take Another Assessment
        </button>
      </div>
    </div>
  );
}
