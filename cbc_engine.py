import re
from collections import Counter


RUBRIC_DESCRIPTORS = {4: "EE", 3: "ME", 2: "AE", 1: "BE"}
REPORTING_BANDS = {
    4: ("EE1", "EE2"),
    3: ("ME1", "ME2"),
    2: ("AE1", "AE2"),
    1: ("BE1", "BE2"),
}
MILESTONE_GRADES = {"Grade 6", "Grade 9"}
JUNIOR_GRADES = {"Grade 7", "Grade 8", "Grade 9"}
SUBJECT_TO_LEARNING_AREA = {
    "MATH": "Mathematics",
    "MAT": "Mathematics",
    "ENG": "English",
    "KISW": "Kiswahili",
    "SCIE": "Science & Technology",
    "INT SCIE": "Integrated Science",
    "PRE-TECH": "Pre-Technical Studies",
    "SST": "Social Studies",
    "AGRI": "Agriculture and Nutrition",
    "C/A": "Creative Arts",
    "CRE": "CRE",
    "REL": "Religious Education",
    "IRE": "IRE",
    "HRE": "HRE",
}


def validate_assessment_number(value):
    assessment_number = str(value or "").strip()
    if not assessment_number or not re.fullmatch(r"[A-Za-z0-9]+", assessment_number):
        raise ValueError("Enter a valid alphanumeric KNEC Assessment Number.")
    return assessment_number


def validate_curriculum(learning_areas, grade, max_junior_areas=9):
    if not isinstance(learning_areas, list):
        raise ValueError("Learning areas must be provided as a list.")
    if grade in JUNIOR_GRADES and len(learning_areas) > max_junior_areas:
        raise ValueError(f"{grade} cannot have more than {max_junior_areas} learning areas.")

    names = set()
    normalized = []
    for area in learning_areas:
        name = str(area.get("name", "")).strip()
        key = name.casefold()
        if not name or key in names:
            raise ValueError("Learning-area names must be present and unique.")
        names.add(key)
        strands = area.get("strands", [])
        if not isinstance(strands, list) or not strands:
            raise ValueError(f"{name} must contain at least one strand.")

        strand_names = set()
        clean_strands = []
        for strand in strands:
            strand_name = str(strand.get("name", "")).strip()
            strand_key = strand_name.casefold()
            if not strand_name or strand_key in strand_names:
                raise ValueError(f"Strand names in {name} must be present and unique.")
            strand_names.add(strand_key)
            sub_strands = strand.get("sub_strands", [])
            if not isinstance(sub_strands, list) or not sub_strands:
                raise ValueError(f"{strand_name} must contain at least one sub-strand.")
            clean_sub_strands = []
            seen_sub_strands = set()
            for sub_strand in sub_strands:
                sub_strand_name = str(sub_strand).strip()
                sub_key = sub_strand_name.casefold()
                if not sub_strand_name or sub_key in seen_sub_strands:
                    raise ValueError(f"Sub-strand names in {strand_name} must be present and unique.")
                seen_sub_strands.add(sub_key)
                clean_sub_strands.append(sub_strand_name)
            clean_strands.append({"name": strand_name, "sub_strands": clean_sub_strands})
        normalized.append({"name": name, "strands": clean_strands})
    return normalized


def rating_from_percentage(percent):
    """Map a percentage mark to rubric level 4-1, or None if it is not a valid percentage."""
    try:
        value = float(percent)
    except (TypeError, ValueError):
        return None
    if not 0 <= value <= 100:
        return None
    if value >= 80:
        return 4
    if value >= 50:
        return 3
    if value >= 30:
        return 2
    return 1


def validate_rubric_rating(value):
    if isinstance(value, str) and value.strip().upper() == "AB":
        return "AB"
    try:
        score = int(value)
    except (TypeError, ValueError):
        raise ValueError("Rubric rating must be 1, 2, 3, 4, or AB.")
    if score not in RUBRIC_DESCRIPTORS:
        raise ValueError("Rubric rating must be 1, 2, 3, 4, or AB.")
    return score


def aggregate_competency(ratings, weights=None):
    """Return the modal rubric descriptor; AB ratings do not contribute."""
    tally = Counter()
    for index, raw_rating in enumerate(ratings):
        rating = validate_rubric_rating(raw_rating)
        if rating == "AB":
            continue
        weight = 1 if weights is None else float(weights[index])
        if weight < 0:
            raise ValueError("Competency weights cannot be negative.")
        tally[rating] += weight
    if not tally:
        return "AB"
    highest_weight = max(tally.values())
    tied_levels = [level for level, weight in tally.items() if weight == highest_weight]
    return RUBRIC_DESCRIPTORS[min(tied_levels)]


def reporting_bands_for_rating(rating):
    score = validate_rubric_rating(rating)
    if score == "AB":
        return ()
    return REPORTING_BANDS[score]


def aggregate_term_competency(formative_ratings, summative_ratings):
    """Apply 70/30 category weights to within-category rubric modes."""
    formative = [validate_rubric_rating(value) for value in formative_ratings]
    summative = [validate_rubric_rating(value) for value in summative_ratings]
    formative = [value for value in formative if value != "AB"]
    summative = [value for value in summative if value != "AB"]
    if not formative or not summative:
        return "Pending"

    category_counts = (Counter(formative), Counter(summative))
    weighted_tallies = Counter()
    for counts, category_weight in zip(category_counts, (0.7, 0.3)):
        count_total = sum(counts.values())
        for level, count in counts.items():
            weighted_tallies[level] += category_weight * count / count_total
    highest_weight = max(weighted_tallies.values())
    tied_levels = [level for level, weight in weighted_tallies.items() if weight == highest_weight]
    return RUBRIC_DESCRIPTORS[min(tied_levels)]


def calculate_milestone_result(
    grade,
    national_percent,
    sba_percent=None,
    grade7_sba_percent=None,
    grade8_sba_percent=None,
):
    if grade not in MILESTONE_GRADES:
        raise ValueError("Weighted national results are supported only for Grade 6 and Grade 9.")
    try:
        national = float(national_percent)
    except (TypeError, ValueError):
        raise ValueError("National assessment result must be a numeric percentage.")
    if not 0 <= national <= 100:
        raise ValueError("National assessment result must be between 0 and 100.")
    if grade == "Grade 6":
        try:
            sba = float(sba_percent)
        except (TypeError, ValueError):
            raise ValueError("Grade 6 SBA result must be a numeric percentage.")
        if not 0 <= sba <= 100:
            raise ValueError("Grade 6 SBA result must be between 0 and 100.")
        return round(sba * 0.4 + national * 0.6, 2)

    try:
        grade7_sba = float(grade7_sba_percent)
        grade8_sba = float(grade8_sba_percent)
    except (TypeError, ValueError):
        raise ValueError("Grade 9 requires separate Grade 7 and Grade 8 SBA percentages.")
    if not 0 <= grade7_sba <= 100 or not 0 <= grade8_sba <= 100:
        raise ValueError("Grade 7 and Grade 8 SBA results must be between 0 and 100.")
    return round(grade7_sba * 0.2 + grade8_sba * 0.2 + national * 0.6, 2)