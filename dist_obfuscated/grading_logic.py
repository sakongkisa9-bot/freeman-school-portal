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
    """Maps total sum to Likuyani scale
    
    Args:
        total_val: Total score or points sum
        is_primary: True for Grade 4-6 (uses raw scores), False for Grade 7-8 (uses points)
        num_subjects: Number of subjects (default 9, used for dynamic threshold calculation)
    """
    if is_primary:
        # Grade 4-6: Using Raw Score Sum (0-900 for 9 subjects)
        # Scale thresholds dynamically based on number of subjects
        max_score_per_subject = 100  # Maximum score per subject
        max_total_score = num_subjects * max_score_per_subject
        
        if max_total_score > 0:
            # Calculate thresholds dynamically based on percentage of maximum possible score
            if total_val >= int(max_total_score * 0.60): return "EE1"  # 60% or higher
            elif total_val >= int(max_total_score * 0.50): return "EE2"  # 50% or higher
            elif total_val >= int(max_total_score * 0.387): return "ME1"  # 38.7% or higher
            elif total_val >= int(max_total_score * 0.273): return "ME2"  # 27.3% or higher
            elif total_val >= int(max_total_score * 0.207): return "AE1"  # 20.7% or higher
            elif total_val >= int(max_total_score * 0.14): return "AE2"  # 14% or higher
            elif total_val >= int(max_total_score * 0.073): return "BE1"  # 7.3% or higher
            return "BE2"
        else:
            return "BE2"
    else:
        # Grade 7-8: Using Points Sum (max 8 points per subject)
        max_points_per_subject = 8  # Maximum points per subject (EE1)
        max_total_points = num_subjects * max_points_per_subject
        
        if max_total_points > 0:
            # Calculate thresholds dynamically based on percentage of maximum possible points
            if total_val >= int(max_total_points * 0.90): return "EE1"  # 90% or higher
            elif total_val >= int(max_total_points * 0.75): return "EE2"  # 75% or higher
            elif total_val >= int(max_total_points * 0.58): return "ME1"  # 58% or higher
            elif total_val >= int(max_total_points * 0.41): return "ME2"  # 41% or higher
            elif total_val >= int(max_total_points * 0.31): return "AE1"  # 31% or higher
            elif total_val >= int(max_total_points * 0.21): return "AE2"  # 21% or higher
            elif total_val >= int(max_total_points * 0.11): return "BE1"  # 11% or higher
            return "BE2"
        else:
            return "BE2"