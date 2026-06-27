import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, CheckCircle, ShieldAlert, Sparkles } from 'lucide-react';

export default function AudioRecorder({ token, API_BASE_URL, sessionId, audioRecorded, setAudioRecorded, speechEmotions, setSpeechEmotions }) {
  const [status, setStatus] = useState('idle'); // idle, recording, processing, success, error
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const streamRef = useRef(null);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      stopRecordingResources();
    };
  }, []);

  const stopRecordingResources = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
  };

  const startRecording = async () => {
    audioChunksRef.current = [];
    setRecordingTime(0);
    setStatus('recording');
    setAudioRecorded(false);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      // Initialize Web Audio API for visualizer
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Draw visualization
      drawWaveform();

      // Setup MediaRecorder
      const options = { mimeType: 'audio/webm' };
      let recorder;
      try {
        recorder = new MediaRecorder(stream, options);
      } catch (e) {
        // Fallback for browsers that don't support audio/webm
        recorder = new MediaRecorder(stream);
      }
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onstop = uploadAudioPayload;

      // Start recording
      recorder.start();

      // Start duration timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 20) { // Limit recordings to 20 seconds for standard diagnostics
            stopRecording();
            return 20;
          }
          return prev + 1;
        });
      }, 1000);

    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  const stopRecording = () => {
    setStatus('processing');
    stopRecordingResources();
  };

  const drawWaveform = () => {
    if (!canvasRef.current || !analyserRef.current) return;
    
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      if (status === 'idle') return;
      animationRef.current = requestAnimationFrame(draw);

      analyser.getByteFrequencyData(dataArray);

      ctx.fillStyle = '#0f111a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 2.5;
      let barHeight;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        barHeight = dataArray[i] / 2;

        // Custom gradient style matching color system
        const gradient = ctx.createLinearGradient(0, canvas.height, 0, canvas.height - barHeight);
        gradient.addColorStop(0, '#6366f1');
        gradient.addColorStop(1, '#06b6d4');

        ctx.fillStyle = gradient;
        ctx.fillRect(x, canvas.height - barHeight, barWidth - 2, barHeight);

        x += barWidth;
      }
    };

    draw();
  };

  const uploadAudioPayload = async () => {
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
    const formData = new FormData();
    formData.append('file', audioBlob, 'assessment.wav');

    try {
      const res = await fetch(`${API_BASE_URL}/assessment/session/${sessionId}/upload-audio`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          setStatus('success');
          setAudioRecorded(true);
          setSpeechEmotions(data.probabilities);
        } else {
          setStatus('error');
        }
      } else {
        setStatus('error');
      }
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '1.5rem', marginBottom: '0' }}>
      <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <Mic size={18} color="#6366f1" /> Voice Recording Module
      </h3>
      <p style={{ fontSize: '0.85rem', color: '#94a3b8', lineHeight: '1.4' }}>
        Please read the following prompt aloud to analyze vocal emotional cues:
        <br />
        <strong style={{ display: 'block', margin: '0.75rem 0', color: '#e2e8f0', fontStyle: 'italic', paddingLeft: '0.5rem', borderLeft: '3px solid #6366f1' }}>
          "Today is a new day. Sometimes I feel overwhelmed, but I am learning to slow down, focus on the present, and accept my feelings without judgment."
        </strong>
      </p>

      {/* Waveform Canvas Visualizer */}
      <canvas 
        ref={canvasRef} 
        className="waveform-canvas" 
        width="400" 
        height="100" 
      />

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1rem' }}>
        {status === 'idle' && (
          <button type="button" onClick={startRecording} className="btn btn-primary">
            <Mic size={16} />
            <span>Record voice prompt</span>
          </button>
        )}

        {status === 'recording' && (
          <button type="button" onClick={stopRecording} className="btn" style={{ background: '#ef4444', color: '#fff' }}>
            <Square size={16} />
            <span>Stop ({recordingTime}s / 20s)</span>
          </button>
        )}

        {status === 'processing' && (
          <div style={{ color: '#06b6d4', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{ animation: 'spin 1s infinite linear', display: 'inline-block' }}>⚙️</span>
            <span>Analyzing voice acoustics...</span>
          </div>
        )}

        {status === 'success' && (
          <div style={{ color: '#10b981', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <CheckCircle size={18} />
            <span>Voice analysis complete!</span>
            <button type="button" onClick={startRecording} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem', marginLeft: '1rem' }}>
              Re-record
            </button>
          </div>
        )}

        {status === 'error' && (
          <div style={{ color: '#ef4444', fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <ShieldAlert size={18} />
            <span>Recording failed. Bypassing voice segment.</span>
            <button type="button" onClick={startRecording} className="btn btn-secondary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem', marginLeft: '1rem' }}>
              Try Again
            </button>
          </div>
        )}
      </div>

      {status === 'success' && speechEmotions && (
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', padding: '1rem', border: '1px solid var(--border-glow)', marginTop: '1.5rem' }}>
          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
            <Sparkles size={14} color="#06b6d4" /> Acoustic Emotion Signature
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            {Object.entries(speechEmotions)
              .filter(([_, val]) => val > 0.05) // Show significant emotions
              .map(([emo, val]) => (
                <div key={emo} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255, 255, 255, 0.01)', padding: '0.4rem 0.75rem', borderRadius: '6px' }}>
                  <span style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>{emo}</span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#6366f1' }}>{Math.round(val * 100)}%</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
