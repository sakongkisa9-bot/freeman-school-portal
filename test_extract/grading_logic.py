# --- grading_logic.py ---

def get_grade_7_8_rating(score):
    """Logic for Junior Secondary (Grade 7-8)"""
    try:
        s = int(score)
        if s >= 90: return "EE1", 8
        elif s >= 75: return "EE2", 7
        elif s >= 58: return "ME1", 6
        elif s >= 41: return "ME2", 5
        elif s >= 31: return "AE1", 4
        elif s >= 21: return "AE2", 3
        elif s >= 11: return "BE1", 2
        else: return "BE2", 1
    except: return "", 0

def get_grade_4_6_rating(score):
    """Logic for Primary (Grade 4-6) - No points needed"""
    try:
        s = int(score)
        if s >= 90: return "EE1"
        elif s >= 75: return "EE2"
        elif s >= 58: return "ME1"
        elif s >= 41: return "ME2"
        elif s >= 31: return "AE1"
        elif s >= 21: return "AE2"
        elif s >= 11: return "BE1"
        else: return "BE2"
    except: return ""

def calculate_final_level(total_val, is_primary=False, num_subjects=9):
    """Maps total sum to KNEC CBC grading scale
    
    Args:
        total_val: Total score or points sum
        is_primary: True for Grade 4-6 (uses raw scores), False for Grade 7-8 (uses points)
        num_subjects: Number of subjects (default 9, used for dynamic threshold calculation)
    """
    if is_primary:
        # Grade 4-6: Using average score per subject (sum of marks / number of subjects)
        # Each subject is scored out of 100
        if num_subjects > 0:
            avg_score = total_val / num_subjects  # Average score per subject (0-100)
            # Use KNEC percentage ranges
            if avg_score >= 90:
                return "EE1"  # 90–100%
            elif avg_score >= 75:
                return "EE2"  # 75–89%
            elif avg_score >= 58:
                return "ME1"  # 58–74%
            elif avg_score >= 41:
                return "ME2"  # 41–57%
            elif avg_score >= 31:
                return "AE1"  # 31–40%
            elif avg_score >= 21:
                return "AE2"  # 21–30%
            elif avg_score >= 11:
                return "BE1"  # 11–20%
            else:
                return "BE2"  # 1–10%
        else:
            return "BE2"
    else:
        # Grade 7-8: Using average score per subject (sum of scores / number of subjects)
        # Each subject is scored out of 100 (converted to points for individual subjects)
        if num_subjects > 0:
            avg_score = total_val / num_subjects  # Average score per subject (0-100)
            # Use KNEC percentage ranges
            if avg_score >= 90:
                return "EE1"  # 90–100%
            elif avg_score >= 75:
                return "EE2"  # 75–89%
            elif avg_score >= 58:
                return "ME1"  # 58–74%
            elif avg_score >= 41:
                return "ME2"  # 41–57%
            elif avg_score >= 31:
                return "AE1"  # 31–40%
            elif avg_score >= 21:
                return "AE2"  # 21–30%
            elif avg_score >= 11:
                return "BE1"  # 11–20%
            else:
                return "BE2"  # 1–10%
        else:
            return "BE2"