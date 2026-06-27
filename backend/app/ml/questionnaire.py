from typing import List, Dict, Any

class QuestionnaireScorer:
    def __init__(self):
        pass

    def score_phq9(self, answers: List[int]) -> Dict[str, Any]:
        """
        Score Patient Health Questionnaire-9 (Depression screening).
        9 items, each rated 0-3. Max score = 27.
        """
        if len(answers) != 9:
            raise ValueError("PHQ-9 requires exactly 9 responses.")
            
        total = sum(answers)
        
        # Severity classifications
        if total <= 4:
            severity = "Minimal Depression"
        elif total <= 9:
            severity = "Mild Depression"
        elif total <= 14:
            severity = "Moderate Depression"
        elif total <= 19:
            severity = "Moderately Severe Depression"
        else:
            severity = "Severe Depression"
            
        return {
            "score": total,
            "max_score": 27,
            "severity": severity,
            "clinical_cut_off": total >= 10, # 10 is standard cutoff for clinical concern
            "normalized_wellbeing": (1.0 - (total / 27.0)) * 100.0
        }

    def score_gad7(self, answers: List[int]) -> Dict[str, Any]:
        """
        Score Generalized Anxiety Disorder-7 (Anxiety screening).
        7 items, each rated 0-3. Max score = 21.
        """
        if len(answers) != 7:
            raise ValueError("GAD-7 requires exactly 7 responses.")
            
        total = sum(answers)
        
        # Severity classifications
        if total <= 4:
            severity = "Minimal Anxiety"
        elif total <= 9:
            severity = "Mild Anxiety"
        elif total <= 14:
            severity = "Moderate Anxiety"
        else:
            severity = "Severe Anxiety"
            
        return {
            "score": total,
            "max_score": 21,
            "severity": severity,
            "clinical_cut_off": total >= 10,
            "normalized_wellbeing": (1.0 - (total / 21.0)) * 100.0
        }

    def score_pss(self, answers: List[int]) -> Dict[str, Any]:
        """
        Score Perceived Stress Scale-10.
        10 items, each rated 0-4. Max score = 40.
        Reverse items: 4, 5, 7, 8 (index 3, 4, 6, 7 in 0-indexed list).
        """
        if len(answers) != 10:
            raise ValueError("PSS requires exactly 10 responses.")
            
        processed_answers = []
        reverse_indices = {3, 4, 6, 7} # Questions 4, 5, 7, 8
        
        for idx, val in enumerate(answers):
            if idx in reverse_indices:
                processed_answers.append(4 - val)
            else:
                processed_answers.append(val)
                
        total = sum(processed_answers)
        
        if total <= 13:
            severity = "Low Stress"
        elif total <= 26:
            severity = "Moderate Stress"
        else:
            severity = "High Stress"
            
        return {
            "score": total,
            "max_score": 40,
            "severity": severity,
            "clinical_cut_off": total >= 27,
            "normalized_wellbeing": (1.0 - (total / 40.0)) * 100.0
        }

    def score_who5(self, answers: List[int]) -> Dict[str, Any]:
        """
        Score WHO-5 Well-being Index.
        5 items, each rated 0-5. Max score = 25.
        Higher score = better well-being.
        """
        if len(answers) != 5:
            raise ValueError("WHO-5 requires exactly 5 responses.")
            
        total = sum(answers)
        percentage_score = total * 4 # Standardized to 0-100 scale
        
        if percentage_score < 50:
            severity = "Poor Well-Being (Depression Risk)"
        else:
            severity = "Good Well-Being"
            
        return {
            "score": total,
            "max_score": 25,
            "percentage_score": percentage_score,
            "severity": severity,
            "clinical_cut_off": percentage_score < 50, # Score < 50 indicates screening for depression
            "normalized_wellbeing": (total / 25.0) * 100.0
        }

    def calculate_overall(self, phq9: List[int], gad7: List[int], pss: List[int], who5: List[int]) -> Dict[str, Any]:
        """
        Calculate unified questionnaire stats and overall score.
        """
        phq_res = self.score_phq9(phq9)
        gad_res = self.score_gad7(gad7)
        pss_res = self.score_pss(pss)
        who_res = self.score_who5(who5)
        
        # Average wellbeing score (0-100)
        overall_score = (
            phq_res["normalized_wellbeing"] +
            gad_res["normalized_wellbeing"] +
            pss_res["normalized_wellbeing"] +
            who_res["normalized_wellbeing"]
        ) / 4.0
        
        return {
            "phq9": phq_res,
            "gad7": gad_res,
            "pss": pss_res,
            "who5": who_res,
            "score": float(overall_score)
        }

questionnaire_scorer = QuestionnaireScorer()
