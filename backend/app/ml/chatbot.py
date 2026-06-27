import requests
import json
import re
from typing import List, Dict, Any
from ..config import settings

class WellBeingChatbot:
    def __init__(self):
        self.disclaimer = (
            "\n\n*Disclaimer: I am an AI companion, not a licensed mental health professional. "
            "If you are experiencing a mental health emergency, please reach out to professional services "
            "or contact emergency responders immediately.*"
        )
        self.crisis_keywords = [
            "suicide", "kill myself", "end my life", "want to die", "hurt myself", 
            "self harm", "cutting", "overdose", "die today", "cannot go on"
        ]

    def _is_crisis(self, message: str) -> bool:
        msg_clean = message.lower().strip()
        for kw in self.crisis_keywords:
            if kw in msg_clean:
                return True
        return False

    def _get_crisis_response(self) -> str:
        return (
            "I hear how much pain you are in right now, and I want to support you, but I am an AI and cannot "
            "provide the crisis support you need. Please reach out to someone who can help. You are not alone.\n\n"
            "**Immediate Help Resources:**\n"
            "📞 **988 Suicide & Crisis Lifeline**: Call or text 988 (Available 24/7, free, confidential).\n"
            "💬 **Crisis Text Line**: Text HOME to 741741 to connect with a crisis counselor.\n"
            "🏥 **Emergency Services**: Call 911 or go to your nearest emergency room."
            + self.disclaimer
        )

    def _offline_fallback(self, message: str) -> str:
        msg = message.lower()
        
        # Simple empathetic reflection rules
        if any(w in msg for w in ["anxious", "anxiety", "panic", "scared", "nervous"]):
            response = (
                "It sounds like you're experiencing a lot of anxiety right now. Anxiety can feel very intense physically, "
                "like a racing heart or shallow breathing. Let's take a slow breath together. Inhale for 4 seconds, hold, "
                "and exhale. Would you like to try a quick grounding exercise, or talk about what's bringing up these feelings?"
            )
        elif any(w in msg for w in ["depressed", "sad", "unhappy", "cry", "lonely", "alone"]):
            response = (
                "I'm really sorry to hear you're feeling down and lonely. It takes strength to share that. When we feel sad, "
                "everything can seem exhausting and heavy. Please be gentle with yourself. It's okay to feel this way. "
                "Is there a small, gentle activity you could do right now, like drinking a warm cup of tea or stepping outside for fresh air?"
            )
        elif any(w in msg for w in ["stressed", "burnout", "work", "exam", "tired", "exhausted"]):
            response = (
                "Stress and burnout can make us feel completely drained. It's often our mind and body telling us we need to pause. "
                "If you can, try to step away from your tasks for just 5 minutes. Try to do a 'mental reset' by stretching. "
                "What is the single biggest stressor on your plate today? Maybe we can break it down."
            )
        elif any(w in msg for w in ["sleep", "insomnia", "awake", "nightmare"]):
            response = (
                "Sleep struggles can make daytime feel twice as hard. Let's focus on calming your environment. Have you tried a "
                "deep breathing exercise or turning off screens? A popular technique is writing down any worries on a sheet of "
                "paper to 'park' them before bedtime."
            )
        elif any(w in msg for w in ["hello", "hi", "hey"]):
            response = (
                "Hello! I am your mental well-being companion. I'm here to listen, offer mindfulness prompts, or help you "
                "decompress. How are you feeling today?"
            )
        else:
            response = (
                "Thank you for sharing that with me. I'm here to listen and support you in a safe, judgment-free space. "
                "It sounds like you are processing a lot. Would you like to share more about what is on your mind, or would "
                "you prefer some mindfulness recommendations?"
            )
            
        return response + self.disclaimer

    def generate_response(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> str:
        """
        Generates response using Google Gemini API if key is available, else falls back to offline empathetic heuristics.
        Also scans for crisis signals to trigger immediate intervention guidelines.
        """
        # 1. Check for crisis
        if self._is_crisis(user_message):
            return self._get_crisis_response()
            
        # 2. Check for API key
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._offline_fallback(user_message)
            
        # 3. Call Gemini API using standard POST request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        
        system_instruction = (
            "You are Talk2Mind AI, a warm, highly empathetic, and professional mental well-being companion. "
            "Your goal is to practice active listening, reflect emotions, provide evidence-based coping tips "
            "(e.g., CBT, mindfulness, breathing), and offer a safe space. "
            "Keep your responses concise, comforting, and conversational (1-3 short paragraphs). "
            "Never diagnose conditions or prescribe medications. Always maintain a supportive tone. "
            "You must not pretend to be a real human or therapist, but a supportive AI agent."
        )
        
        # Build contents structure for chat history
        contents = []
        if chat_history:
            # Add recent context (max 10 messages for speed)
            for msg in chat_history[-10:]:
                role = "user" if msg["sender"] == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["message"]}]
                })
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })
            
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 300
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=8)
            if response.status_code == 200:
                res_data = response.json()
                bot_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                return bot_text.strip() + self.disclaimer
            else:
                print(f"Gemini API returned error: {response.text}")
                return self._offline_fallback(user_message)
        except Exception as e:
            print(f"Failed to communicate with Gemini API: {e}")
            return self._offline_fallback(user_message)

chatbot = WellBeingChatbot()
