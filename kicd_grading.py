"""KICD four-level grading: formative (70%) from sub-strand levels, summative exam (30%), final rating."""

import math

ABSENT = "AB"
NOT_AVAILABLE = "n/a"
LEVEL_POINTS = {"EE": 4, "ME": 3, "AE": 2, "BE": 1}
POINTS_LEVEL = {points: level for level, points in LEVEL_POINTS.items()}
FORMATIVE_WEIGHT = 70
SUMMATIVE_WEIGHT = 30


def level_from_percent(percent):
    """80-100 EE, 50-79 ME, 30-49 AE, 0-29 BE; None when not a valid percentage."""
    try:
        value = float(percent)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or not 0 <= value <= 100:
        return None
    if value >= 80:
        return "EE"
    if value >= 50:
        return "ME"
    if value >= 30:
        return "AE"
    return "BE"


def _points(level):
    text = str(level).strip().upper()
    if text in LEVEL_POINTS:
        return LEVEL_POINTS[text]
    if text in {"1", "2", "3", "4"}:
        return int(text)
    return None


def formative_raw(sub_strand_levels):
    """Mean points of the filled sub-strands; absent or empty entries are ignored."""
    points = [value for value in map(_points, sub_strand_levels) if value is not None]
    return sum(points) / len(points) if points else None


def formative_level(raw):
    """Nearest level to the mean points, with .5 rounding up (3.5 is EE)."""
    if raw is None:
        return None
    return POINTS_LEVEL[min(4, max(1, int(math.floor(raw + 0.5))))]


def formative_weighted(raw):
    """Formative mean converted to its 70% share."""
    return None if raw is None else raw / 4 * FORMATIVE_WEIGHT


def index_levels(records):
    """Group portal rows [assessment number, learner, area, strand, sub-strand, level] by learner."""
    index = {}
    for record in records:
        if len(record) < 6:
            continue
        number, learner, _area, _strand, _sub_strand, level = record[:6]
        keys = [
            key
            for key in (str(number or "").strip().lower(), "".join(str(learner or "").split()).lower())
            if key
        ]
        bucket = next((index[key] for key in keys if key in index), None)
        if bucket is None:
            bucket = []
        bucket.append(level)
        for key in keys:
            index.setdefault(key, bucket)
    return index


def levels_for(index, assessment_number, name):
    for key in (str(assessment_number or "").strip().lower(), "".join(str(name or "").split()).lower()):
        if key and key in index:
            return index[key]
    return []


def subject_result(sub_strand_levels, exam_percent):
    """Return the F, S and R cells for one subject and the final percentage."""
    raw = formative_raw(sub_strand_levels)
    absent = str(exam_percent).strip().upper() == ABSENT
    try:
        exam = None if absent else float(exam_percent)
    except (TypeError, ValueError):
        exam = None

    f_cell = NOT_AVAILABLE if raw is None else f"{raw:.1f} ({formative_level(raw)})"
    if absent:
        return {"F": f_cell, "S": ABSENT, "R": ABSENT, "final_percent": None}
    if exam is None:
        return {"F": f_cell, "S": "", "R": "", "final_percent": None}

    s_cell = f"{exam:g}%"
    if raw is None:
        return {"F": f_cell, "S": s_cell, "R": level_from_percent(exam) or "", "final_percent": exam}
    final = formative_weighted(raw) + exam * SUMMATIVE_WEIGHT / 100
    return {"F": f_cell, "S": s_cell, "R": level_from_percent(final) or "", "final_percent": round(final, 2)}
