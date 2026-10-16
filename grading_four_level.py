"""Four-level (EE, ME, AE, BE) drop-in replacements for the old eight-level grading helpers."""

from kicd_grading import LEVEL_POINTS, level_from_percent


def get_grade_4_6_rating(score):
    try:
        return level_from_percent(int(score)) or ""
    except (TypeError, ValueError):
        return ""


def get_grade_7_8_rating(score):
    level = get_grade_4_6_rating(score)
    return level, LEVEL_POINTS.get(level, 0)


calculate_junior_grade = get_grade_7_8_rating


def calculate_final_level(total_val, is_primary=False, num_subjects=9):
    """Level of the average score per subject."""
    if num_subjects <= 0:
        return "BE"
    return level_from_percent(min(100, max(0, total_val / num_subjects))) or "BE"


ABSENT = "AB"
PARTIAL_ABSENT_LEVEL = "X"
ALL_ABSENT_LEVEL = "Y"


def absent_average_level(scores):
    """'Y' if every subject is AB, 'X' if some are AB, otherwise None."""
    marks = [str(s).strip().upper() if s is not None else "" for s in scores]
    absent = sum(1 for m in marks if m == ABSENT)
    if absent == 0:
        return None
    return ALL_ABSENT_LEVEL if absent == len(marks) else PARTIAL_ABSENT_LEVEL


def rank_key(total, level):
    """Sort key: students with X/Y average level always rank after everyone else."""
    return (level in (PARTIAL_ABSENT_LEVEL, ALL_ABSENT_LEVEL), -(total or 0))


def is_absent_level(level):
    return level in (PARTIAL_ABSENT_LEVEL, ALL_ABSENT_LEVEL)
