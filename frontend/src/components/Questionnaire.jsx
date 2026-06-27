import React, { useState } from 'react';
import { Sparkles, ArrowRight, ShieldCheck, Heart, AlertCircle, ArrowLeft } from 'lucide-react';
import RealTimeVisualizer from './RealTimeVisualizer';
import AudioRecorder from './AudioRecorder';

export default function Questionnaire({ token, API_BASE_URL, setActiveTab }) {
  const [stage, setStage] = useState(0); // 0: intro, 1: webcam, 2: voice, 3: phq9/gad7, 4: pss/who5, 5: complete/loading
  const [sessionId, setSessionId] = useState(null);
  
  // Modality completion triggers
  const [webcamActive, setWebcamActive] = useState(false);
  const [webcamEmotions, setWebcamEmotions] = useState(null);
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceEmotions, setVoiceEmotions] = useState(null);

  // Questionnaire responses state arrays
  const [phq9Answers, setPhq9Answers] = useState(Array(9).fill(-1));
  const [gad7Answers, setGad7Answers] = useState(Array(7).fill(-1));
  const [pssAnswers, setPssAnswers] = useState(Array(10).fill(-1));
  const [who5Answers, setWho5Answers] = useState(Array(5).fill(-1));
  const [errorMsg, setErrorMsg] = useState('');

  // Start Assessment
  const handleStartSession = async () => {
    setErrorMsg('');
    try {
      const res = await fetch(`${API_BASE_URL}/assessment/session/start`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSessionId(data.id);
        setStage(1); // Proceed to Webcam stage
      } else {
        setErrorMsg('Failed to initialize diagnostic session. Please try again.');
      }
    } catch (err) {
      setErrorMsg('Error connecting to servers.');
    }
  };

  // Questions Database
  const phq9Questions = [
    "Little interest or pleasure in doing things",
    "Feeling down, depressed, or hopeless",
    "Trouble falling or staying asleep, or sleeping too much",
    "Feeling tired or having little energy",
    "Poor appetite or overeating",
    "Feeling bad about yourself — or that you are a failure or have let yourself or your family down",
    "Trouble concentrating on things, such as reading the newspaper or watching television",
    "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual",
    "Thoughts that you would be better off dead or of hurting yourself in some way"
  ];

  const gad7Questions = [
    "Feeling nervous, anxious, or on edge",
    "Not being able to stop or control worrying",
    "Worrying too much about different things",
    "Trouble relaxing",
    "Being so restless that it is hard to sit still",
    "Becoming easily annoyed or irritable",
    "Feeling afraid as if something awful might happen"
  ];

  const pssQuestions = [
    "In the last month, how often have you been upset because of something that happened unexpectedly?",
    "In the last month, how often have you felt that you were unable to control the important things in your life?",
    "In the last month, how often have you felt nervous and stressed?",
    "In the last month, how often have you felt confident about your ability to handle your personal problems?",
    "In the last month, how often have you felt that things were going your way?",
    "In the last month, how often have you found that you could not cope with all the things that you had to do?",
    "In the last month, how often have you been able to control irritations in your life?",
    "In the last month, how often have you felt that you were on top of things?",
    "In the last month, how often have you been angered because of things that happened that were outside of your control?",
    "In the last month, how often have you felt difficulties were piling up so high that you could not overcome them?"
  ];

  const who5Questions = [
    "I have felt cheerful and in good spirits",
    "I have felt calm and relaxed",
    "I have felt active and vigorous",
    "I have woke up feeling fresh and rested",
    "My daily life has been filled with things that interest me"
  ];

  // Options labels mapping
  const standardOptions = [
    { label: "Not at all", value: 0 },
    { label: "Several days", value: 1 },
    { label: "More than half the days", value: 2 },
    { label: "Nearly every day", value: 3 }
  ];

  const pssOptions = [
    { label: "Never", value: 0 },
    { label: "Almost Never", value: 1 },
    { label: "Sometimes", value: 2 },
    { label: "Fairly Often", value: 3 },
    { label: "Very Often", value: 4 }
  ];

  const who5Options = [
    { label: "At no time", value: 0 },
    { label: "Some of the time", value: 1 },
    { label: "Less than half the time", value: 2 },
    { label: "More than half the time", value: 3 },
    { label: "Most of the time", value: 4 },
    { label: "All of the time", value: 5 }
  ];

  const handleSelectOption = (scale, index, value) => {
    if (scale === 'phq9') {
      const updated = [...phq9Answers];
      updated[index] = value;
      setPhq9Answers(updated);
    } else if (scale === 'gad7') {
      const updated = [...gad7Answers];
      updated[index] = value;
      setGad7Answers(updated);
    } else if (scale === 'pss') {
      const updated = [...pssAnswers];
      updated[index] = value;
      setPssAnswers(updated);
    } else if (scale === 'who5') {
      const updated = [...who5Answers];
      updated[index] = value;
      setWho5Answers(updated);
    }
  };

  const validateStage = () => {
    setErrorMsg('');
    if (stage === 3) {
      if (phq9Answers.includes(-1) || gad7Answers.includes(-1)) {
        setErrorMsg('Please answer all PHQ-9 and GAD-7 questions before proceeding.');
        return false;
      }
    } else if (stage === 4) {
      if (pssAnswers.includes(-1) || who5Answers.includes(-1)) {
        setErrorMsg('Please answer all PSS-10 and WHO-5 questions before submission.');
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStage()) {
      setStage(prev => prev + 1);
    }
  };

  const handleSubmit = async () => {
    if (!validateStage()) return;
    setStage(5); // Show loading state
    
    try {
      const res = await fetch(`${API_BASE_URL}/assessment/session/${sessionId}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          phq9: phq9Answers,
          gad7: gad7Answers,
          pss: pssAnswers,
          who5: who5Answers
        })
      });

      if (res.ok) {
        // Redirect to dashboard to inspect final charts
        setActiveTab('dashboard');
      } else {
        const errorData = await res.json();
        setErrorMsg(errorData.detail || 'Submission failed.');
        setStage(4); // Keep on last stage
      }
    } catch (err) {
      setErrorMsg('Failed to sync results to database.');
      setStage(4);
    }
  };

  return (
    <div className="animated-view" style={{ maxWidth: '850px', margin: '0 auto' }}>
      
      {/* Intro Stage */}
      {stage === 0 && (
        <div className="glass-panel text-center" style={{ padding: '3.5rem 2.5rem' }}>
          <div className="logo-icon" style={{ display: 'inline-flex', padding: '12px', marginBottom: '1.5rem' }}>
            <Heart size={32} color="#fff" />
          </div>
          <h1 style={{ fontSize: '2.5rem', marginBottom: '0.75rem', color: '#fff' }}>Multimodal Wellness Assessment</h1>
          <p style={{ color: '#94a3b8', fontSize: '1.05rem', maxWidth: '600px', margin: '0 auto 2.5rem auto', lineHeight: '1.5' }}>
            Talk2Mind analyzes multiple biometric and cognitive markers (facial expression tracking, voice acoustic diagnostics, and standardized questionnaires) to generate your comprehensive Well-Being Index.
          </p>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '2.5rem', textAlign: 'left' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-glow)' }}>
              <h4 style={{ color: '#818cf8', fontSize: '0.95rem', marginBottom: '0.5rem' }}>1. Webcam Tracking</h4>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Tracks facial micro-expressions to gauge positive emotional valence.</p>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-glow)' }}>
              <h4 style={{ color: '#06b6d4', fontSize: '0.95rem', marginBottom: '0.5rem' }}>2. Voice Acoustics</h4>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Extracts speech energy, pitch shifts, and tempo during a short voice prompt.</p>
            </div>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1.25rem', borderRadius: '12px', border: '1px solid var(--border-glow)' }}>
              <h4 style={{ color: '#d946ef', fontSize: '0.95rem', marginBottom: '0.5rem' }}>3. Standardized Surveys</h4>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Measures stress, anxiety, and depression indicators using PHQ-9 & GAD-7.</p>
            </div>
          </div>

          {errorMsg && (
            <div style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '1.5rem' }}>{errorMsg}</div>
          )}

          <button onClick={handleStartSession} className="btn btn-primary" style={{ padding: '1rem 2rem', fontSize: '1.05rem' }}>
            <span>Begin Guided Assessment</span>
            <ArrowRight size={18} />
          </button>
        </div>
      )}

      {/* Stage 1: Webcam Biometrics */}
      {stage === 1 && (
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#818cf8', fontWeight: 700, letterSpacing: '0.05em' }}>Step 1 of 4</span>
              <h2 style={{ fontSize: '1.5rem', color: '#fff', marginTop: '0.25rem' }}>Visual Biometrics Capture</h2>
            </div>
            <button onClick={handleNext} className="btn btn-primary">
              <span>Next Step</span>
              <ArrowRight size={16} />
            </button>
          </div>
          
          <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '1.5rem', lineHeight: '1.4' }}>
            Turn on your webcam below. The system will track micro-expressions for a few moments to establish emotional baseline valence indicators. If you do not have a camera, you can turn it off to skip.
          </p>

          <RealTimeVisualizer 
            token={token}
            API_BASE_URL={API_BASE_URL}
            sessionId={sessionId}
            isRecording={webcamActive}
            setIsRecording={setWebcamActive}
            activeEmotions={webcamEmotions}
            setActiveEmotions={setWebcamEmotions}
          />
        </div>
      )}

      {/* Stage 2: Voice Biometrics */}
      {stage === 2 && (
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#06b6d4', fontWeight: 700, letterSpacing: '0.05em' }}>Step 2 of 4</span>
              <h2 style={{ fontSize: '1.5rem', color: '#fff', marginTop: '0.25rem' }}>Speech Acoustics Recording</h2>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button onClick={() => setStage(1)} className="btn btn-secondary"><ArrowLeft size={16} /> Back</button>
              <button onClick={handleNext} className="btn btn-primary"><span>Next Step</span><ArrowRight size={16} /></button>
            </div>
          </div>

          <AudioRecorder 
            token={token}
            API_BASE_URL={API_BASE_URL}
            sessionId={sessionId}
            audioRecorded={voiceActive}
            setAudioRecorded={setVoiceActive}
            speechEmotions={voiceEmotions}
            setSpeechEmotions={setVoiceEmotions}
          />
        </div>
      )}

      {/* Stage 3: PHQ-9 & GAD-7 Questionnaire */}
      {stage === 3 && (
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#d946ef', fontWeight: 700, letterSpacing: '0.05em' }}>Step 3 of 4</span>
              <h2 style={{ fontSize: '1.5rem', color: '#fff', marginTop: '0.25rem' }}>Mood & Anxiety Screeners</h2>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button onClick={() => setStage(2)} className="btn btn-secondary"><ArrowLeft size={16} /> Back</button>
              <button onClick={handleNext} className="btn btn-primary"><span>Next Step</span><ArrowRight size={16} /></button>
            </div>
          </div>

          <p style={{ fontSize: '0.85rem', color: '#94a3b8', marginBottom: '1.5rem' }}>
            Over the <strong>last 2 weeks</strong>, how often have you been bothered by any of the following problems?
          </p>

          {errorMsg && (
            <div style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '1.5rem' }}>{errorMsg}</div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#818cf8', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>PHQ-9 (Depression Screener)</h3>
              {phq9Questions.map((q, idx) => (
                <div key={`phq-${idx}`} className="question-card">
                  <p className="question-text">{idx+1}. {q}</p>
                  <div className="options-flex">
                    {standardOptions.map(opt => (
                      <button 
                        key={opt.value}
                        type="button"
                        className={`option-btn ${phq9Answers[idx] === opt.value ? 'selected' : ''}`}
                        onClick={() => handleSelectOption('phq9', idx, opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#06b6d4', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>GAD-7 (Anxiety Screener)</h3>
              {gad7Questions.map((q, idx) => (
                <div key={`gad-${idx}`} className="question-card">
                  <p className="question-text">{idx+1}. {q}</p>
                  <div className="options-flex">
                    {standardOptions.map(opt => (
                      <button 
                        key={opt.value}
                        type="button"
                        className={`option-btn ${gad7Answers[idx] === opt.value ? 'selected' : ''}`}
                        onClick={() => handleSelectOption('gad7', idx, opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stage 4: PSS & WHO-5 Questionnaire */}
      {stage === 4 && (
        <div className="glass-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
            <div>
              <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: '#d946ef', fontWeight: 700, letterSpacing: '0.05em' }}>Step 4 of 4</span>
              <h2 style={{ fontSize: '1.5rem', color: '#fff', marginTop: '0.25rem' }}>Stress & Well-Being Indexes</h2>
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button onClick={() => setStage(3)} className="btn btn-secondary"><ArrowLeft size={16} /> Back</button>
              <button onClick={handleSubmit} className="btn btn-primary"><span>Submit Assessment</span><ShieldCheck size={16} /></button>
            </div>
          </div>

          {errorMsg && (
            <div style={{ color: '#ef4444', fontSize: '0.85rem', marginBottom: '1.5rem' }}>{errorMsg}</div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#818cf8', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>Perceived Stress Scale (PSS-10)</h3>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>In the <strong>last month</strong>, how often have you felt or thought about the following?</p>
              {pssQuestions.map((q, idx) => (
                <div key={`pss-${idx}`} className="question-card">
                  <p className="question-text">{idx+1}. {q}</p>
                  <div className="options-flex">
                    {pssOptions.map(opt => (
                      <button 
                        key={opt.value}
                        type="button"
                        className={`option-btn ${pssAnswers[idx] === opt.value ? 'selected' : ''}`}
                        onClick={() => handleSelectOption('pss', idx, opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div>
              <h3 style={{ fontSize: '1.1rem', color: '#06b6d4', marginBottom: '1rem', borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: '0.5rem' }}>WHO-5 (Well-Being Index)</h3>
              <p style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1rem' }}>Over the <strong>last 2 weeks</strong>, how often have you felt this way?</p>
              {who5Questions.map((q, idx) => (
                <div key={`who5-${idx}`} className="question-card">
                  <p className="question-text">{idx+1}. {q}</p>
                  <div className="options-flex">
                    {who5Options.map(opt => (
                      <button 
                        key={opt.value}
                        type="button"
                        className={`option-btn ${who5Answers[idx] === opt.value ? 'selected' : ''}`}
                        onClick={() => handleSelectOption('who5', idx, opt.value)}
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Stage 5: Processing Submit */}
      {stage === 5 && (
        <div className="glass-panel text-center" style={{ padding: '4rem 2rem' }}>
          <div style={{ display: 'inline-block', position: 'relative', width: '80px', height: '80px', marginBottom: '2rem' }}>
            <div style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              border: '4px solid rgba(99, 102, 241, 0.1)',
              borderRadius: '50%'
            }} />
            <div style={{
              position: 'absolute',
              width: '100%',
              height: '100%',
              border: '4px solid transparent',
              borderTopColor: '#6366f1',
              borderRadius: '50%',
              animation: 'spin 1s infinite linear'
            }} />
          </div>
          <h2 style={{ fontSize: '1.75rem', marginBottom: '0.5rem', color: '#fff' }}>Fusing Biometric Features</h2>
          <p style={{ color: '#94a3b8', fontSize: '0.95rem', maxWidth: '400px', margin: '0 auto' }}>
            Integrating facial emotions, acoustic speech patterns, and cognitive responses to generate your Mental Well-Being Index...
          </p>
        </div>
      )}

    </div>
  );
}
