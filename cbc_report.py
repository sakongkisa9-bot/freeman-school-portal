from collections import OrderedDict
import math

from kicd_grading import subject_result


LEVEL_VALUES = {"BE": 1, "AE": 2, "ME": 3, "EE": 4}
VALUE_LEVELS = {value: level for level, value in LEVEL_VALUES.items()}
CHART_MARKERS = ("circle", "square", "triangle", "cross", "diamond")
PATHWAY_SUBJECTS = OrderedDict(
    (
        ("STEM", ("Mathematics", "Integrated Science", "Science & Technology", "Pre-Technical Studies", "Agriculture and Nutrition")),
        ("Social Sciences", ("English", "Kiswahili", "Social Studies", "Religious Education")),
        ("Arts and Sports Science", ("Creative Arts and Sports", "Creative Arts", "English", "Kiswahili", "Physical Education")),
    )
)


def normalize_level(value):
    text = str(value or "").strip().upper()
    if text == "AB":
        return "AB"
    for level in LEVEL_VALUES:
        if text == level or text.startswith(level):
            return level
    try:
        return VALUE_LEVELS.get(int(float(text)), "")
    except (TypeError, ValueError):
        return ""


def chart_marker_for_subject(subject_index):
    return CHART_MARKERS[subject_index % len(CHART_MARKERS)]


def group_rubric_records(records):
    subjects = OrderedDict()
    for record in records or []:
        if len(record) < 6:
            continue
        _assessment_number, _learner, area, strand, sub_strand, raw_level = record[:6]
        evidence = str(record[6] or "").strip() if len(record) > 6 else ""
        area = str(area or "Learning Area").strip()
        strand = str(strand or "").strip()
        sub_strand = str(sub_strand or "").strip()
        if not strand or not sub_strand:
            continue
        subject = subjects.setdefault(area, OrderedDict())
        strand_rows = subject.setdefault(strand, OrderedDict())
        strand_rows[sub_strand] = {
            "level": normalize_level(raw_level),
            "evidence": evidence,
        }

    result = []
    for area, strands in subjects.items():
        sub_strands = [
            {"strand": strand, "name": name, **item}
            for strand, entries in strands.items()
            for name, item in entries.items()
        ]
        recommendations = recommend_substrands(sub_strands)
        result.append(
            {
                "name": area,
                "strands": [
                    {
                        "name": strand,
                        "sub_strands": [
                            {"name": name, **item}
                            for name, item in entries.items()
                        ],
                    }
                    for strand, entries in strands.items()
                ],
                "recommendations": recommendations,
            }
        )
    return result


def build_subject_results(subject_areas, current_marks, records):
    score_keys = {
        _subject_token(key[:-2]): value
        for key, value in (current_marks or {}).items()
        if str(key).endswith("_s")
    }
    results = []
    for subject, area in subject_areas:
        area_records = [
            row for row in records or []
            if len(row) >= 6 and str(row[2]).strip().casefold() == str(area).strip().casefold()
        ]
        score = score_keys.get(_subject_token(subject), "")
        levels = [row[5] for row in area_records]
        result = subject_result(levels, score)
        composite_score = result["final_percent"]
        if composite_score is not None:
            composite_score = int(math.floor(composite_score + 0.5))
        results.append(
            {
                "subject": subject,
                "area": area,
                "formative": result["F"],
                "summative": result["S"],
                "rating": result["R"],
                "composite_score": composite_score,
                "records": area_records,
            }
        )
    return results


def _subject_token(value):
    token = "".join(character for character in str(value or "").casefold() if character.isalnum())
    return {
        "math": "mathematics", "mat": "mathematics", "eng": "english",
        "kisw": "kiswahili", "intsci": "integratedscience", "intscie": "integratedscience",
        "scie": "sciencetechnology", "sci": "sciencetechnology",
        "pretech": "pretechnicalstudies", "agri": "agricultureandnutrition",
        "ca": "creativeartsandsports", "arts": "creativeartsandsports",
        "sst": "socialstudies", "rel": "religiouseducation",
    }.get(token, token)


def recommend_substrands(sub_strands):
    marked = [
        item for item in sub_strands
        if item.get("level") in LEVEL_VALUES
    ]
    values = sorted(LEVEL_VALUES[item["level"]] for item in marked)
    if len(set(values)) < 2:
        return []

    midpoint = (values[(len(values) - 1) // 2] + values[len(values) // 2]) / 2
    lowest_two = set(sorted(set(values))[:2])
    recommended_levels = {value for value in values if value < midpoint and value in lowest_two}
    if not recommended_levels:
        recommended_levels = {min(values)}
    return [
        {"strand": item.get("strand", ""), "name": item["name"], "level": item["level"]}
        for item in marked
        if LEVEL_VALUES[item["level"]] in recommended_levels
    ]


def build_teacher_comments(subject_results, rubric_subjects=None, student_name=""):
    valid = [
        item for item in subject_results or []
        if item.get("rating") in LEVEL_VALUES
    ]
    if not valid:
        message = "More assessment evidence is needed before a learner-specific comment can be made."
        return {"class_teacher": message, "head_teacher": message}

    learner = str(student_name or "The learner").strip().title()
    strongest = [item["area"] for item in valid if item["rating"] == "EE"]
    meeting = [item["area"] for item in valid if item["rating"] == "ME"]
    developing = [item["area"] for item in valid if item["rating"] == "AE"]
    revisit_by_area = OrderedDict()
    for subject in rubric_subjects or []:
        for item in subject.get("recommendations", []):
            revisit_by_area.setdefault(subject["name"], []).append(item["name"])
    revisit = [
        f"{area} ({', '.join(names[:3])})"
        for area, names in revisit_by_area.items()
    ]

    strengths = strongest or meeting
    if strengths:
        strength_text = ", ".join(strengths[:3])
        class_comment = f"Well done, {learner}. You are showing strong attainment in {strength_text}."
    else:
        class_comment = f"{learner}, you are building understanding across the assessed learning areas."

    focus = revisit or developing
    if focus:
        focus_text = ", ".join(focus[:3])
        class_comment += f" For your next steps, focus on {focus_text}."
        head_comment = f"{learner}, work with your teacher to strengthen {focus_text} through guided examples and regular practice."
    elif strongest:
        head_comment = f"{learner}, extend your strong work in {', '.join(strongest[:3])} by applying these skills to new and more challenging tasks."
    else:
        head_comment = f"{learner}, keep practicing the skills covered this term and ask for feedback when a task is challenging."

    if len(strongest) == len(valid):
        class_comment = f"Excellent work, {learner}. You are exceeding expectations across {', '.join(strongest[:3])}. Keep challenging yourself."
        head_comment = f"{learner}, your consistent attainment is commendable. Apply these skills in new contexts and continue aiming higher."

    return {"class_teacher": class_comment, "head_teacher": head_comment}


def percentage(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 100 else None


def pathway_scores(subject_scores):
    normalized = {str(name).strip().casefold(): percentage(score) for name, score in (subject_scores or {}).items()}
    aliases = {
        "math": "mathematics",
        "mat": "mathematics",
        "eng": "english",
        "kisw": "kiswahili",
        "int sci": "integrated science",
        "int scie": "integrated science",
        "scie": "science & technology",
        "sci": "science & technology",
        "pre-tech": "pre-technical studies",
        "agri": "agriculture and nutrition",
        "c/a": "creative arts and sports",
        "arts": "creative arts and sports",
        "sst": "social studies",
        "rel": "religious education",
        "cre": "religious education",
        "ire": "religious education",
        "hre": "religious education",
        "re": "religious education",
        "lang": "english",
        "env": "science & technology",
        "creat": "creative arts and sports",
        "lit": "english",
    }
    for alias, canonical in aliases.items():
        if alias in normalized and canonical not in normalized:
            normalized[canonical] = normalized[alias]

    result = []
    for name, subjects in PATHWAY_SUBJECTS.items():
        scores = [normalized.get(subject.casefold()) for subject in subjects]
        available = [score for score in scores if score is not None]
        result.append(
            {
                "name": name,
                "subjects": list(subjects),
                "subject_scores": [
                    {"name": subject, "score": normalized.get(subject.casefold())}
                    for subject in subjects
                ],
                "score": round(sum(available) / len(available), 1) if available else None,
            }
        )
    return result


def pathway_recommendation(current_scores, history_scores=None, term=""):
    current = pathway_scores(current_scores)
    ranked = sorted(
        (item for item in current if item["score"] is not None),
        key=lambda item: item["score"],
        reverse=True,
    )
    if not ranked:
        return {"pathways": current, "recommended": "", "basis": "No learning-area ratings are available yet."}

    recommended = ranked[0]["name"]
    exam_history = [pathway_scores(scores) for scores in (history_scores or [])]
    best_by_exam = []
    for exam in exam_history + [current]:
        available = [item for item in exam if item["score"] is not None]
        if available:
            best_by_exam.append(max(available, key=lambda item: item["score"])["name"])
    consistent_count = sum(path == recommended for path in best_by_exam)
    consistent = (
        len(best_by_exam) >= 3 and consistent_count / len(best_by_exam) >= (2 / 3)
    ) or (
        str(term).strip().casefold() == "term 3"
        and len(best_by_exam) >= 2
        and consistent_count / len(best_by_exam) >= (2 / 3)
    )
    basis = (
        "Performance across exams consistently aligns with this pathway."
        if consistent
        else "Indicative match for this exam only; review again as more assessment history becomes available."
    )
    return {
        "pathways": current,
        "recommended": recommended,
        "basis": basis,
        "consistent": consistent,
    }