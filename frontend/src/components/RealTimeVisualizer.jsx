import React, { useEffect, useRef, useState } from 'react';
import { Camera, CameraOff, Video, AlertCircle } from 'lucide-react';

export default function RealTimeVisualizer({ token, API_BASE_URL, sessionId, isRecording, setIsRecording, activeEmotions, setActiveEmotions }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const intervalRef = useRef(null);
  const [error, setError] = useState('');
  const [currentFaceBox, setCurrentFaceBox] = useState(null);
  const [dominantEmotion, setDominantEmotion] = useState('Neutral');

  useEffect(() => {
    if (isRecording) {
      startCamera();
    } else {
      stopCamera();
    }

    return () => {
      stopCamera();
    };
  }, [isRecording]);

  const startCamera = async () => {
    setError('');
    setCurrentFaceBox(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 }
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      // Start frame submission loop (every 1200ms for responsiveness)
      intervalRef.current = setInterval(captureAndSubmitFrame, 1200);
    } catch (err) {
      console.error(err);
      setError('Webcam access denied or unavailable. Visual biometrics will be bypassed.');
      setIsRecording(false);
    }
  };

  const stopCamera = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setCurrentFaceBox(null);
  };

  const captureAndSubmitFrame = async () => {
    if (!videoRef.current || !canvasRef.current || !streamRef.current) return;
    
    const video = videoRef.current;
    const canvas = canvasRef.current;
    
    // Ensure video is playing and has dimensions
    if (video.videoWidth === 0) return;
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    try {
      const base64Frame = canvas.toDataURL('image/jpeg', 0.6); // 60% quality compression for performance
      
      const res = await fetch(`${API_BASE_URL}/assessment/session/${sessionId}/analyze-frame`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ frame: base64Frame })
      });
      
      if (res.ok) {
        const data = await res.json();
        
        if (data.detected) {
          setDominantEmotion(data.emotion);
          setActiveEmotions(data.probabilities);
          
          // Map backend face coordinates (relative/absolute) to video element client bounds
          const box = data.details?.box; // [x, y, w, h] — optional chaining guards against missing details
          if (box && videoRef.current) {
            const videoElem = videoRef.current;
            const clientWidth = videoElem.clientWidth;
            const clientHeight = videoElem.clientHeight;
            
            // Scalers
            const scaleX = clientWidth / video.videoWidth;
            const scaleY = clientHeight / video.videoHeight;
            
            setCurrentFaceBox({
              left: box[0] * scaleX,
              top: box[1] * scaleY,
              width: box[2] * scaleX,
              height: box[3] * scaleY
            });
          }
        } else {
          setCurrentFaceBox(null);
        }
      }
    } catch (err) {
      console.error("Frame upload error:", err);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div className="webcam-container">
        <video 
          ref={videoRef} 
          className="webcam-video" 
          autoPlay 
          playsInline 
          muted 
        />
        
        {/* Render bounding face box in real time */}
        {currentFaceBox && (
          <div className="face-box" style={{
            left: `${currentFaceBox.left}px`,
            top: `${currentFaceBox.top}px`,
            width: `${currentFaceBox.width}px`,
            height: `${currentFaceBox.height}px`
          }}>
            <span className="face-label">{dominantEmotion}</span>
          </div>
        )}

        {/* Hidden processing canvas */}
        <canvas ref={canvasRef} style={{ display: 'none' }} />

        {/* Off State Mask Overlay */}
        {!isRecording && (
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: 'rgba(11, 12, 18, 0.95)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1rem',
            color: '#64748b'
          }}>
            <CameraOff size={40} style={{ opacity: 0.6 }} />
            <p style={{ fontSize: '0.9rem' }}>Webcam biometrics deactivated.</p>
          </div>
        )}
      </div>

      {error && (
        <div style={{
          display: 'flex',
          gap: '0.5rem',
          background: 'rgba(245, 158, 11, 0.08)',
          border: '1px solid rgba(245, 158, 11, 0.25)',
          borderRadius: '10px',
          padding: '0.8rem',
          color: '#fbbf24',
          fontSize: '0.8rem',
          alignItems: 'center'
        }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button 
          type="button"
          onClick={() => setIsRecording(!isRecording)} 
          className={`btn ${isRecording ? 'btn-secondary' : 'btn-accent'}`}
        >
          {isRecording ? <CameraOff size={16} /> : <Camera size={16} />}
          <span>{isRecording ? 'Turn Off Webcam' : 'Turn On Webcam'}</span>
        </button>

        {isRecording && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: '#ef4444',
              animation: 'pulse 1s infinite alternate'
            }} />
            <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>Live facial tracking active</span>
          </div>
        )}
      </div>

      {isRecording && activeEmotions && (
        <div style={{ background: 'rgba(255, 255, 255, 0.02)', borderRadius: '12px', padding: '1rem', border: '1px solid var(--border-glow)' }}>
          <h4 style={{ fontSize: '0.85rem', textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: '0.75rem' }}>
            Emotional Valence Real-Time Distributions
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {Object.entries(activeEmotions).map(([emo, val]) => (
              <div key={emo} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ width: '80px', fontSize: '0.85rem', color: '#fff' }}>{emo}</span>
                <div style={{ flexGrow: 1, height: '6px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{
                    width: `${val * 100}%`,
                    height: '100%',
                    background: emo === 'Happy' || emo === 'Neutral' ? 'var(--color-secondary)' : 'var(--color-primary)',
                    borderRadius: '3px',
                    transition: 'width 0.2s ease'
                  }} />
                </div>
                <span style={{ width: '35px', textAlign: 'right', fontSize: '0.8rem', color: '#94a3b8' }}>
                  {Math.round(val * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
