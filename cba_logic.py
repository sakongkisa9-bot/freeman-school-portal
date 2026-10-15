LEVEL_NAMES = ("Level 1", "Level 2", "Level 3", "Level 4")


def absence_mark_for_grade(grade):
    return "AB"


def validate_tasks(tasks):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("Add at least one task before publishing.")

    validated = []
    task_names = set()
    for task in tasks:
        name = str(task.get("name", "")).strip()
        if not name:
            raise ValueError("Every task needs a name.")
        normalized_name = name.casefold()
        if normalized_name in task_names:
            raise ValueError(f"Task names must be unique: {name}")
        task_names.add(normalized_name)

        if task.get("mode", "levels") == "max":
            try:
                max_score = int(task["max_score"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"Enter a numeric maximum score for {name}.")
            if max_score < 1:
                raise ValueError(f"Maximum score for {name} must be at least 1.")
            validated.append(
                {
                    "name": name,
                    "unit": str(task.get("unit", "")).strip(),
                    "mode": "max",
                    "max_score": max_score,
                }
            )
            continue

        ranges = task.get("ranges", {})
        validated_ranges = {}
        occupied = []
        for level in LEVEL_NAMES:
            criterion = ranges.get(level)
            if not isinstance(criterion, dict):
                raise ValueError(f"{name} is missing the {level} range.")
            rule_type = criterion.get("type", "range")
            if rule_type == "range":
                try:
                    minimum = int(criterion["min"])
                    maximum = int(criterion["max"])
                except (KeyError, TypeError, ValueError):
                    raise ValueError(
                        f"Enter numeric minimum and maximum for {name}, {level}."
                    )
                if minimum < 0 or maximum < minimum:
                    raise ValueError(f"Invalid range for {name}, {level}.")
                occupied.append((minimum, maximum, level))
                validated_ranges[level] = {
                    "type": "range",
                    "min": minimum,
                    "max": maximum,
                }
            elif rule_type in {"exact", "above", "at_least"}:
                try:
                    value = int(criterion["value"])
                except (KeyError, TypeError, ValueError):
                    raise ValueError(f"Enter a numeric value for {name}, {level}.")
                if value < 0:
                    raise ValueError(f"Invalid value for {name}, {level}.")
                validated_ranges[level] = {"type": rule_type, "value": value}
                if rule_type == "exact":
                    occupied.append((value, value, level))
                elif rule_type == "above":
                    occupied.append((value + 1, None, level))
                else:
                    occupied.append((value, None, level))
            else:
                raise ValueError(f"Unknown criterion type for {name}, {level}.")

        occupied.sort(key=lambda interval: interval[0])
        for previous, current in zip(occupied, occupied[1:]):
            if previous[1] is None or current[0] <= previous[1]:
                raise ValueError(f"Ranges overlap for task {name}.")

        validated.append(
            {
                "name": name,
                "unit": str(task.get("unit", "")).strip(),
                "mode": "levels",
                "ranges": validated_ranges,
            }
        )
    return validated


def convert_raw_score(task, raw_score):
    if isinstance(raw_score, str) and raw_score.strip().upper() == "AB":
        return {"level": "AB", "points": None}
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        raise ValueError("Raw score must be a whole number.")
    if score < 0:
        raise ValueError("Raw score cannot be negative.")

    if task.get("mode") == "max":
        if score > int(task["max_score"]):
            raise ValueError(
                f"Raw score {score} is above the maximum of {task['max_score']}."
            )
        # Max-score tasks are reported as the raw score itself.
        return {"level": "Score", "points": score}

    for level in reversed(LEVEL_NAMES):
        criterion = task.get("ranges", {}).get(level, {})
        rule_type = criterion.get("type", "range")
        if rule_type == "range":
            matches = int(criterion.get("min", 0)) <= score <= int(
                criterion.get("max", -1)
            )
        elif rule_type == "exact":
            matches = score == int(criterion.get("value", -1))
        elif rule_type == "above":
            matches = score > int(criterion.get("value", -1))
        elif rule_type == "at_least":
            matches = score >= int(criterion.get("value", -1))
        else:
            matches = False
        if matches:
            return {"level": level, "points": int(level.rsplit(" ", 1)[1])}
    raise ValueError(f"Raw score {score} does not match a configured level range.")


def task_score_bounds(task):
    if task.get("mode") == "max":
        return 0, int(task["max_score"])
    ranges = task.get("ranges", {}).values()
    minima = []
    maxima = []
    has_no_upper_bound = False
    for criterion in ranges:
        rule_type = criterion.get("type", "range")
        if rule_type == "range":
            minima.append(int(criterion["min"]))
            maxima.append(int(criterion["max"]))
        elif rule_type == "exact":
            value = int(criterion["value"])
            minima.append(value)
            maxima.append(value)
        elif rule_type == "above":
            minima.append(int(criterion["value"]) + 1)
            has_no_upper_bound = True
        elif rule_type == "at_least":
            minima.append(int(criterion["value"]))
            has_no_upper_bound = True
    return min(minima), None if has_no_upper_bound else max(maxima)


def describe_criterion(criterion, unit=""):
    rule_type = criterion.get("type", "range")
    if rule_type == "range":
        description = f"{criterion['min']}–{criterion['max']}"
    elif rule_type == "exact":
        description = str(criterion["value"])
    elif rule_type == "above":
        description = f"Above {criterion['value']}"
    else:
        description = f"At least {criterion['value']}"
    return f"{description} {unit}".strip()