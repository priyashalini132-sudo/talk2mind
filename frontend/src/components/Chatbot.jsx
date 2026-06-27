import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  MessageSquare, Send, BrainCircuit, RefreshCw, AlertTriangle, Mic, Square
} from 'lucide-react';

const QUICK_PROMPTS = [
  "I'm feeling anxious today",
  "How can I improve my sleep?",
  "Give me a breathing exercise",
  "I'm struggling to focus",
  "Help me manage stress",
  "I feel overwhelmed",
];

const DISCLAIMER = "⚠️ I am an AI wellness companion, not a licensed therapist. This conversation is for support and information only — not medical advice. If you are in crisis, please call 988 (US) or text HOME to 741741.";

export default function Chatbot({ token, API_BASE_URL }) {
  const [messages, setMessages] = useState([
    {
      sender: 'bot',
      text: `Hello! I'm your AI wellness companion. I can help you with stress management, breathing techniques, mindfulness practices, sleep hygiene, and general mental wellness strategies.\n\n${DISCLAIMER}`,
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const messagesEndRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;
    const userMsg = { sender: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/chatbot/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ message: text }),
      });

      if (res.ok) {
        const data = await res.json();
        setMessages(prev => [...prev, { sender: 'bot', text: data.reply }]);
      } else {
        setMessages(prev => [...prev, {
          sender: 'bot',
          text: "I'm sorry, I couldn't process that right now. Please try again.",
        }]);
      }
    } catch {
      setMessages(prev => [...prev, {
        sender: 'bot',
        text: "Connection issue. Please check that the server is running.",
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleClear = async () => {
    setMessages([{
      sender: 'bot',
      text: `Chat cleared. How can I support your wellness journey today?\n\n${DISCLAIMER}`,
    }]);
  };

  const startVoiceInput = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      audioChunksRef.current = [];
      recorder.ondataavailable = e => audioChunksRef.current.push(e.data);
      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        transcribeAndSend(blob);
        stream.getTracks().forEach(t => t.stop());
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      alert('Microphone access required for voice input.');
    }
  };

  const stopVoiceInput = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const transcribeAndSend = (blob) => {
    // Browser speech API fallback
    const recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (recognition) {
      const rec = new recognition();
      rec.onresult = (e) => {
        const transcript = e.results[0][0].transcript;
        sendMessage(transcript);
      };
      rec.onerror = () => {
        sendMessage("(Voice message – transcription unavailable)");
      };
      rec.start();
    } else {
      sendMessage("(Voice message received)");
    }
  };

  return (
    <div className="animated-view" style={{ maxWidth: 780, margin: '0 auto' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h1 style={{ fontSize: '1.9rem', marginBottom: '0.3rem' }}>Wellness Chat</h1>
        <p style={{ color: '#94a3b8', fontSize: '0.88rem' }}>
          AI-powered wellness companion · Not a substitute for professional care
        </p>
      </div>

      <div className="glass-panel" style={{ marginBottom: 0 }}>
        {/* Chat Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid var(--border-glow)' }}>
          <div className="logo-icon" style={{ width: 36, height: 36, borderRadius: 10 }}>
            <BrainCircuit size={18} color="#fff" />
          </div>
          <div>
            <h4 style={{ fontSize: '0.92rem', color: '#fff', fontWeight: 600 }}>MindCompanion AI</h4>
            <span style={{ fontSize: '0.72rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981', display: 'inline-block' }} />
              Online · Educational purposes only
            </span>
          </div>
          <button
            className="btn btn-secondary"
            onClick={handleClear}
            style={{ marginLeft: 'auto', fontSize: '0.8rem', padding: '0.45rem 0.9rem', gap: '0.4rem' }}
          >
            <RefreshCw size={14} /> Clear
          </button>
        </div>

        {/* Messages */}
        <div className="chatbot-messages">
          {messages.map((msg, i) => (
            <div key={i} className={`message-bubble ${msg.sender}`}>
              {msg.text.split('\n').map((line, j) => (
                <span key={j}>{line}{j < msg.text.split('\n').length - 1 && <br />}</span>
              ))}
            </div>
          ))}
          {loading && (
            <div className="message-bubble bot" style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', padding: '0.85rem 1.1rem' }}>
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#94a3b8', animation: 'pulse-ring 1s ease-in-out 0s infinite' }} />
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#94a3b8', animation: 'pulse-ring 1s ease-in-out 0.2s infinite' }} />
              <div style={{ width: 7, height: 7, borderRadius: '50%', background: '#94a3b8', animation: 'pulse-ring 1s ease-in-out 0.4s infinite' }} />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Quick Prompts */}
        <div className="quick-prompts">
          {QUICK_PROMPTS.map((p, i) => (
            <button key={i} className="quick-prompt-chip" onClick={() => sendMessage(p)}>
              {p}
            </button>
          ))}
        </div>

        {/* Input Area */}
        <div className="chat-input-area">
          <input
            className="input-field"
            placeholder="Type your message... (Enter to send)"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
            style={{ flex: 1 }}
          />
          <button
            className={`btn ${isRecording ? 'btn-danger' : 'btn-secondary'}`}
            onClick={isRecording ? stopVoiceInput : startVoiceInput}
            title={isRecording ? 'Stop recording' : 'Voice input'}
            style={{ padding: '0.75rem', minWidth: 44 }}
          >
            {isRecording ? <Square size={16} /> : <Mic size={16} />}
          </button>
          <button
            className="btn btn-primary"
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            style={{ padding: '0.75rem 1.1rem' }}
          >
            <Send size={16} />
          </button>
        </div>

        {/* Disclaimer Banner */}
        <div style={{ marginTop: '1rem', padding: '0.7rem 0.9rem', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: '10px', display: 'flex', gap: '0.6rem', alignItems: 'flex-start' }}>
          <AlertTriangle size={14} color="#f59e0b" style={{ flexShrink: 0, marginTop: 2 }} />
          <p style={{ fontSize: '0.75rem', color: '#92400e', lineHeight: '1.4', color: '#fbbf24' }}>
            This AI is for informational support only and is not a licensed mental health professional. 
            In emergencies, call <strong>988</strong> (US) or your local crisis line.
          </p>
        </div>
      </div>
    </div>
  );
}
