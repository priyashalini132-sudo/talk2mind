"""
Talk2Mind – Personalized Recommendation Engine
===============================================
Generates evidence-based mental wellness recommendations based on:
    - Fused well-being score (0–100)
    - Clinical classification label
    - PHQ-9, GAD-7, PSS, WHO-5 subscale scores

Recommendation categories:
    1. Breathing techniques (diaphragmatic, paced, HRV-based)
    2. Mindfulness exercises (MBSR-informed)
    3. Journaling prompts (CBT-inspired)
    4. Music suggestions (music therapy principles)
    5. Sleep hygiene advice (sleep medicine guidelines)
    6. Exercise plans (physical activity for mental health)
    7. Positive affirmations (strengths-based)
    8. Professional help resources (crisis lines, therapy referrals)

All content is for educational and informational purposes only.
References professional guidelines from APA, WHO, NIMH, and SAMHSA.
"""

from typing import Dict, Any, List, Optional


class RecommendationEngine:
    """
    Personalised mental wellness recommendation generator.
    
    Uses a tiered content library with classification-aware selection logic.
    Recommendations are weighted by clinical subscale severity.
    """

    # ──────────────────────────────────────────────────────────────────────────
    # Content Library
    # ──────────────────────────────────────────────────────────────────────────

    BREATHING_LIBRARY = {
        "4-7-8 Technique": {
            "description": "Inhale deeply for 4 seconds, hold for 7, exhale slowly for 8. "
                           "Activates the parasympathetic nervous system.",
            "duration": "5 minutes", "intensity": "low", "evidence": "Clinical",
        },
        "Box Breathing (Navy SEAL)": {
            "description": "Inhale 4s → Hold 4s → Exhale 4s → Hold 4s. "
                           "Used by military professionals to manage acute stress response.",
            "duration": "4 minutes", "intensity": "low", "evidence": "Clinical",
        },
        "Coherent Breathing (5/5)": {
            "description": "5 seconds in, 5 seconds out at ~6 breaths/minute. "
                           "Optimises heart rate variability (HRV) and vagal tone.",
            "duration": "10 minutes", "intensity": "low", "evidence": "Research-backed",
        },
        "Diaphragmatic Breathing": {
            "description": "Place one hand on chest, one on belly. Breathe so only the belly rises. "
                           "Reduces cortisol and lowers blood pressure.",
            "duration": "5 minutes", "intensity": "low", "evidence": "Clinical",
        },
        "Alternate Nostril (Nadi Shodhana)": {
            "description": "Block right nostril, inhale left; block left, exhale right. "
                           "Balances nervous system hemispheres. Rooted in pranayama yoga.",
            "duration": "7 minutes", "intensity": "low", "evidence": "Research-backed",
        },
    }

    MINDFULNESS_LIBRARY = {
        "Body Scan Meditation": {
            "description": "Lie down comfortably. Slowly scan your awareness from feet to head, "
                           "noticing sensations without judgment. MBSR-based technique.",
            "duration": "15 minutes", "type": "MBSR",
        },
        "5-4-3-2-1 Grounding": {
            "description": "Name 5 things you see, 4 you can touch, 3 you hear, "
                           "2 you smell, 1 you taste. Interrupts anxiety spirals.",
            "duration": "3 minutes", "type": "Grounding",
        },
        "Mindful Walking": {
            "description": "Walk slowly for 10 minutes focusing entirely on the "
                           "sensation of each footstep. No phone, no destination.",
            "duration": "10 minutes", "type": "Movement",
        },
        "Loving-Kindness (Metta)": {
            "description": "Silently repeat: 'May I be happy. May I be healthy. May I be safe.' "
                           "Expand to others. Reduces self-criticism and isolation.",
            "duration": "12 minutes", "type": "Compassion",
        },
        "Observing Thoughts": {
            "description": "Sit quietly and watch thoughts arise and pass like clouds. "
                           "Label them ('planning', 'worrying') without engaging.",
            "duration": "8 minutes", "type": "ACT-based",
        },
        "Mindful Journaling": {
            "description": "Spend 5 minutes writing observations about your present moment — "
                           "what you notice in your body, environment, and emotions.",
            "duration": "5 minutes", "type": "Reflective",
        },
    }

    JOURNALING_LIBRARY = {
        "Gratitude List": {
            "prompt": "Write 3 things you are genuinely grateful for today. "
                      "For each one, describe *why* it matters to you.",
            "type": "Positive Psychology",
        },
        "Cognitive Reframing": {
            "prompt": "Describe one negative thought you had today. "
                      "Now write 2 alternative, balanced interpretations of the same situation.",
            "type": "CBT",
        },
        "Stream of Consciousness": {
            "prompt": "Set a 5-minute timer. Write without stopping, editing, or pausing — "
                      "whatever is in your mind. Don't read it after.",
            "type": "Expressive Writing",
        },
        "Emotion Naming": {
            "prompt": "Write about what you are feeling right now in as much detail as possible. "
                      "Name the emotion precisely (not just 'bad' — 'frustrated', 'disappointed', etc.).",
            "type": "Affect Labelling",
        },
        "Values Clarification": {
            "prompt": "List 3 of your core personal values. Write about a recent time when you "
                      "lived in alignment with each one, and one time you didn't.",
            "type": "ACT",
        },
        "Best Possible Self": {
            "prompt": "Imagine yourself in 5 years, having achieved your most important goals. "
                      "Write a detailed description of that version of you.",
            "type": "Positive Psychology",
        },
    }

    MUSIC_LIBRARY = {
        "Binaural Beats – Theta (4–7 Hz)": {
            "description": "Use headphones. Theta waves induce deep relaxation and creative states. "
                           "Best for anxiety relief and pre-sleep wind-down.",
            "platform": "YouTube / Spotify – search 'Theta Binaural Beats'",
        },
        "Binaural Beats – Alpha (8–12 Hz)": {
            "description": "Alpha waves promote calm focus and stress reduction. "
                           "Ideal for mild stress or work sessions.",
            "platform": "YouTube / Spotify – search 'Alpha Binaural Beats'",
        },
        "Ambient Nature Sounds": {
            "description": "Rainfall, ocean waves, or forest acoustics. "
                           "Scientifically shown to reduce cortisol and improve sleep quality.",
            "platform": "YouTube / Calm App / Spotify – 'Nature Sounds'",
        },
        "Uplifting Classical": {
            "description": "Beethoven's 'Ode to Joy', Mozart's Symphony No. 40, or Vivaldi's 'Spring'. "
                           "Shown to elevate mood and improve cognitive performance.",
            "platform": "Spotify Classical / Apple Music Classical",
        },
        "Soft Acoustic / Lo-Fi": {
            "description": "Gentle guitar, piano, or lo-fi hip-hop without lyrics. "
                           "Reduces cognitive load while maintaining wakefulness.",
            "platform": "Spotify – 'Lo-Fi Beats' / YouTube Music",
        },
        "Solfeggio Frequencies (528 Hz)": {
            "description": "Claimed to promote DNA repair and emotional healing in sound therapy. "
                           "Relaxation benefits are supported by HRV research.",
            "platform": "YouTube – search '528 Hz Healing Music'",
        },
    }

    SLEEP_LIBRARY = {
        "Digital Sunset": {
            "description": "Power down all screens 60 minutes before bed. "
                           "Blue light suppresses melatonin by up to 50% (Harvard, 2012).",
        },
        "Sleep Environment Optimisation": {
            "description": "Ideal sleep: 65–68°F (18–20°C), complete darkness, white noise. "
                           "Cool temperatures accelerate sleep onset.",
        },
        "Chamomile Tea Ritual": {
            "description": "Drink chamomile or passionflower herbal tea 30 minutes before bed. "
                           "Apigenin in chamomile binds GABA receptors.",
        },
        "Progressive Muscle Relaxation (PMR)": {
            "description": "Tense each muscle group for 5 seconds, then release for 30. "
                           "Start from toes and work upward. Reduces insomnia by 30–40%.",
        },
        "Consistent Sleep Schedule": {
            "description": "Wake up at the same time every day — even weekends. "
                           "This anchors your circadian rhythm and improves sleep quality.",
        },
        "4-7-8 Pre-Sleep Breathing": {
            "description": "Use the 4-7-8 breathing technique in bed. "
                           "Activates the vagus nerve and induces sleepiness.",
        },
    }

    EXERCISE_LIBRARY = {
        "Brisk Walking (20 min)": {
            "description": "A 20-minute brisk walk releases endorphins without spiking cortisol. "
                           "Equivalent antidepressant effect to medication for mild depression (Blumenthal, 1999).",
            "frequency": "Daily", "intensity": "Low",
        },
        "Yoga – Yin (60 min)": {
            "description": "Deep stretching with 2–5 minute holds per pose. "
                           "Stimulates parasympathetic nervous system. Best for anxiety and overactivation.",
            "frequency": "3x/week", "intensity": "Low",
        },
        "Yoga – Vinyasa Flow (45 min)": {
            "description": "Dynamic, breath-synchronised movement. Builds strength while "
                           "processing emotional tension through physical exertion.",
            "frequency": "3x/week", "intensity": "Moderate",
        },
        "Swimming (30 min)": {
            "description": "Repetitive bilateral movement with rhythmic breathing. "
                           "Exceptionally effective for depression and trauma processing.",
            "frequency": "3x/week", "intensity": "Moderate",
        },
        "HIIT (20 min)": {
            "description": "High-intensity intervals (20s on, 10s off). "
                           "Maximally boosts BDNF (brain-derived neurotrophic factor).",
            "frequency": "2x/week", "intensity": "High",
        },
        "Progressive Muscle Relaxation": {
            "description": "Systematically tense and release muscle groups for 20 minutes. "
                           "Physical embodiment of calm. Zero equipment needed.",
            "frequency": "Daily", "intensity": "Very Low",
        },
    }

    AFFIRMATIONS_LIBRARY = {
        "Healthy": [
            "I am in a good place and I choose to nurture this state daily.",
            "My mental wellness is a priority and I invest in it every day.",
            "I am resilient, capable, and growing.",
        ],
        "Mild Stress": [
            "I can handle this challenge — I've overcome difficulties before.",
            "It's okay to feel stressed. I breathe through it with patience.",
            "Every day I take one small step toward balance.",
        ],
        "Moderate Stress": [
            "I release what I cannot control and focus on what I can.",
            "I am stronger than my stress. I choose peace over pressure.",
            "I deserve rest, support, and kindness — especially from myself.",
        ],
        "High Stress": [
            "I am not my worst day. This too shall pass.",
            "Reaching out for help is an act of courage, not weakness.",
            "I honour my body's signals. I slow down and breathe.",
        ],
        "Anxiety Risk": [
            "My thoughts are not facts. I can observe them without believing them.",
            "I am safe in this present moment.",
            "I choose to respond, not react. I have the power to pause.",
        ],
        "Depression Risk": [
            "I matter. My existence has value even when I cannot feel it.",
            "Small steps are still forward movement. I celebrate any progress.",
            "I deserve support and I will ask for it today.",
        ],
    }

    PROFESSIONAL_RESOURCES = [
        {
            "name": "SAMHSA National Helpline",
            "contact": "1-800-662-4357",
            "description": "Free, confidential, 24/7 treatment referral and information service.",
            "url": "https://www.samhsa.gov/find-help/national-helpline",
        },
        {
            "name": "988 Suicide & Crisis Lifeline",
            "contact": "Call or Text 988",
            "description": "Immediate access to trained mental health crisis counsellors.",
            "url": "https://988lifeline.org",
        },
        {
            "name": "Crisis Text Line",
            "contact": "Text HOME to 741741",
            "description": "Free 24/7 mental health support via SMS.",
            "url": "https://www.crisistextline.org",
        },
        {
            "name": "BetterHelp (Online Therapy)",
            "contact": "betterhelp.com",
            "description": "Connect with a licensed therapist online within 48 hours.",
            "url": "https://www.betterhelp.com",
        },
        {
            "name": "Psychology Today Therapist Finder",
            "contact": "psychologytoday.com/us/therapists",
            "description": "Find a local therapist filtered by insurance, specialty, and approach.",
            "url": "https://www.psychologytoday.com/us/therapists",
        },
    ]

    # ──────────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────────

    def generate_recommendations(
        self,
        score: float,
        classification: str,
        q_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a personalised, tiered recommendation set.

        Returns:
            {
                "breathing":         [str, ...],
                "mindfulness":       [str, ...],
                "journaling":        [str, ...],
                "music":             [str, ...],
                "sleep":             [str, ...],
                "exercise":          [str, ...],
                "affirmations":      [str, ...],
                "weekly_plan":       [{day, activities}, ...],
                "professional_help": Optional[dict],
            }
        """
        phq = q_results["phq9"]["score"]
        gad = q_results["gad7"]["score"]
        pss = q_results["pss"]["score"]
        who = q_results["who5"]["score"]

        recs: Dict[str, Any] = {
            "breathing":      [],
            "mindfulness":    [],
            "journaling":     [],
            "music":          [],
            "sleep":          [],
            "exercise":       [],
            "affirmations":   [],
            "weekly_plan":    [],
            "professional_help": None,
        }

        # ── Tier selection ────────────────────────────────────────────────────
        if classification in ("Depression Risk", "Anxiety Risk", "High Stress"):
            self._fill_tier_severe(recs, classification, phq, gad, pss)
        elif classification in ("Moderate Stress",):
            self._fill_tier_moderate(recs, phq, gad)
        elif classification in ("Mild Stress",):
            self._fill_tier_mild(recs)
        else:  # Healthy
            self._fill_tier_healthy(recs)

        # ── Affirmations ──────────────────────────────────────────────────────
        recs["affirmations"] = self.AFFIRMATIONS_LIBRARY.get(
            classification, self.AFFIRMATIONS_LIBRARY["Mild Stress"]
        )

        # ── Weekly wellness plan ──────────────────────────────────────────────
        recs["weekly_plan"] = self._generate_weekly_plan(classification)

        # ── Professional help (triggered for high-risk) ───────────────────────
        if classification in ("Depression Risk", "Anxiety Risk", "High Stress") or phq >= 15 or gad >= 15:
            recs["professional_help"] = {
                "triggered": True,
                "reason": (
                    f"Your assessment indicates significant indicators of {classification}. "
                    "We strongly encourage connecting with a mental health professional. "
                    "This tool is a screening aid — not a diagnostic instrument."
                ),
                "resources": self.PROFESSIONAL_RESOURCES,
            }

        return recs

    # ──────────────────────────────────────────────────────────────────────────
    # Tier fillers
    # ──────────────────────────────────────────────────────────────────────────

    def _fill_tier_severe(
        self, recs: Dict, classification: str, phq: int, gad: int, pss: int
    ) -> None:
        """High-intensity recommendations for high stress / anxiety / depression."""
        recs["breathing"] = [
            self._fmt_breathing("4-7-8 Technique"),
            self._fmt_breathing("Box Breathing (Navy SEAL)"),
        ]
        recs["mindfulness"] = [
            self._fmt_mindfulness("5-4-3-2-1 Grounding"),
            self._fmt_mindfulness("Body Scan Meditation"),
        ]
        recs["journaling"] = [
            self._fmt_journaling("Cognitive Reframing"),
            self._fmt_journaling("Emotion Naming"),
        ]
        if classification == "Depression Risk" or phq >= 10:
            recs["music"] = [
                self._fmt_music("Uplifting Classical"),
                self._fmt_music("Binaural Beats – Alpha (8–12 Hz)"),
            ]
            recs["exercise"] = [
                self._fmt_exercise("Brisk Walking (20 min)"),
                self._fmt_exercise("Yoga – Yin (60 min)"),
            ]
        else:  # Anxiety / High Stress
            recs["music"] = [
                self._fmt_music("Binaural Beats – Theta (4–7 Hz)"),
                self._fmt_music("Ambient Nature Sounds"),
            ]
            recs["exercise"] = [
                self._fmt_exercise("Progressive Muscle Relaxation"),
                self._fmt_exercise("Yoga – Yin (60 min)"),
            ]
        recs["sleep"] = [
            self._fmt_sleep("Digital Sunset"),
            self._fmt_sleep("4-7-8 Pre-Sleep Breathing"),
            self._fmt_sleep("Progressive Muscle Relaxation (PMR)"),
        ]

    def _fill_tier_moderate(self, recs: Dict, phq: int, gad: int) -> None:
        recs["breathing"] = [
            self._fmt_breathing("Box Breathing (Navy SEAL)"),
            self._fmt_breathing("Coherent Breathing (5/5)"),
        ]
        recs["mindfulness"] = [
            self._fmt_mindfulness("Mindful Walking"),
            self._fmt_mindfulness("5-4-3-2-1 Grounding"),
        ]
        recs["journaling"] = [
            self._fmt_journaling("Gratitude List"),
            self._fmt_journaling("Cognitive Reframing"),
        ]
        recs["music"] = [self._fmt_music("Ambient Nature Sounds")]
        recs["sleep"] = [
            self._fmt_sleep("Sleep Environment Optimisation"),
            self._fmt_sleep("Consistent Sleep Schedule"),
        ]
        recs["exercise"] = [
            self._fmt_exercise("Brisk Walking (20 min)"),
            self._fmt_exercise("Yoga – Vinyasa Flow (45 min)"),
        ]

    def _fill_tier_mild(self, recs: Dict) -> None:
        recs["breathing"] = [self._fmt_breathing("Coherent Breathing (5/5)")]
        recs["mindfulness"] = [
            self._fmt_mindfulness("Mindful Walking"),
            self._fmt_mindfulness("Observing Thoughts"),
        ]
        recs["journaling"] = [
            self._fmt_journaling("Gratitude List"),
            self._fmt_journaling("Best Possible Self"),
        ]
        recs["music"] = [self._fmt_music("Soft Acoustic / Lo-Fi")]
        recs["sleep"] = [self._fmt_sleep("Sleep Environment Optimisation")]
        recs["exercise"] = [self._fmt_exercise("Brisk Walking (20 min)")]

    def _fill_tier_healthy(self, recs: Dict) -> None:
        recs["breathing"] = [self._fmt_breathing("Alternate Nostril (Nadi Shodhana)")]
        recs["mindfulness"] = [self._fmt_mindfulness("Loving-Kindness (Metta)")]
        recs["journaling"] = [
            self._fmt_journaling("Gratitude List"),
            self._fmt_journaling("Values Clarification"),
        ]
        recs["music"] = [self._fmt_music("Uplifting Classical")]
        recs["sleep"] = [self._fmt_sleep("Consistent Sleep Schedule")]
        recs["exercise"] = [
            self._fmt_exercise("Brisk Walking (20 min)"),
            self._fmt_exercise("HIIT (20 min)"),
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Weekly plan generator
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_weekly_plan(self, classification: str) -> List[Dict]:
        """Generate a 7-day wellness plan."""
        DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        if classification in ("Depression Risk", "Anxiety Risk", "High Stress"):
            activities = [
                ["Morning: 4-7-8 breathing (5 min)", "Evening: Body scan meditation (15 min)"],
                ["Morning: Brisk walk (20 min)", "Night: Journaling – Emotion Naming"],
                ["Morning: Box breathing (4 min)", "Evening: Yin yoga (30 min)", "Night: Digital sunset"],
                ["Morning: 5-4-3-2-1 grounding", "Afternoon: Binaural beats while resting"],
                ["Morning: Diaphragmatic breathing", "Evening: PMR before sleep"],
                ["Full day: Low-screen, outdoor time", "Evening: Chamomile tea ritual"],
                ["Reflection: Review your week's journal entries", "Plan next week's intentions"],
            ]
        elif classification in ("Moderate Stress",):
            activities = [
                ["Morning: Coherent breathing (10 min)", "Evening: Gratitude list"],
                ["Exercise: 20-min brisk walk", "Night: Sleep environment setup"],
                ["Morning: Mindful walking (10 min)", "Evening: Lo-fi music session"],
                ["Journaling: Cognitive reframing exercise"],
                ["Exercise: Vinyasa yoga (45 min)"],
                ["Morning: Nature sounds meditation", "Afternoon: Screen-free creative activity"],
                ["Evening: Review and set intentions for the week"],
            ]
        else:  # Mild Stress / Healthy
            activities = [
                ["Morning: 5-min Nadi Shodhana breathing"],
                ["Exercise: Brisk walk or jog (20 min)", "Journal: Best Possible Self"],
                ["Morning: Loving-Kindness meditation (12 min)"],
                ["Evening: Classical music relaxation"],
                ["Exercise: HIIT (20 min)"],
                ["Morning: Outdoor mindful walk", "Evening: Values clarification journal"],
                ["Rest day: Gratitude list + gentle stretching"],
            ]

        return [
            {"day": DAYS[i], "activities": activities[i]}
            for i in range(7)
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Formatters
    # ──────────────────────────────────────────────────────────────────────────

    def _fmt_breathing(self, key: str) -> str:
        item = self.BREATHING_LIBRARY[key]
        return f"**{key}** ({item['duration']}): {item['description']}"

    def _fmt_mindfulness(self, key: str) -> str:
        item = self.MINDFULNESS_LIBRARY[key]
        return f"**{key}** [{item['type']}] ({item['duration']}): {item['description']}"

    def _fmt_journaling(self, key: str) -> str:
        item = self.JOURNALING_LIBRARY[key]
        return f"**{key}** [{item['type']}]: {item['prompt']}"

    def _fmt_music(self, key: str) -> str:
        item = self.MUSIC_LIBRARY[key]
        return f"**{key}**: {item['description']} | Platform: {item['platform']}"

    def _fmt_sleep(self, key: str) -> str:
        item = self.SLEEP_LIBRARY[key]
        return f"**{key}**: {item['description']}"

    def _fmt_exercise(self, key: str) -> str:
        item = self.EXERCISE_LIBRARY[key]
        return (f"**{key}** ({item['frequency']}, {item['intensity']} intensity): "
                f"{item['description']}")


# ─── Singleton instance ───────────────────────────────────────────────────────
recommendation_engine = RecommendationEngine()
