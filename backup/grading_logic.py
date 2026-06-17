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

def calculate_final_level(total_val, is_primary=False):
    """Maps total sum to Likuyani scale"""
    if is_primary:
        # Grade 4-6: Using Raw Score Sum (0-900)
        if total_val >= 540: return "EE1"
        elif total_val >= 450: return "EE2"
        elif total_val >= 348: return "ME1"
        elif total_val >= 246: return "ME2"
        elif total_val >= 186: return "AE1"
        elif total_val >= 126: return "AE2"
        elif total_val >= 66: return "BE1"
        return "BE2"
    else:
        # Grade 7-8: Using Points Sum (0-72)
        if total_val >= 66: return "EE1"
        elif total_val >= 58: return "EE2"
        elif total_val >= 48: return "ME1"
        elif total_val >= 38: return "ME2"
        elif total_val >= 28: return "AE1"
        elif total_val >= 18: return "AE2"
        elif total_val >= 9: return "BE1"
        return "BE2"