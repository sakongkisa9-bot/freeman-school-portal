LEVEL_NAMES = ("Level 1", "Level 2", "Level 3", "Level 4")


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

        ranges = task.get("ranges", {})
        validated_ranges = {}
        occupied = []
        for level in LEVEL_NAMES:
            level_range = ranges.get(level)
            if not isinstance(level_range, dict):
                raise ValueError(f"{name} is missing the {level} range.")
            try:
                minimum = int(level_range["min"])
                maximum = int(level_range["max"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"Enter numeric minimum and maximum for {name}, {level}.")
            if minimum < 0 or maximum < minimum:
                raise ValueError(f"Invalid range for {name}, {level}.")
            occupied.append((minimum, maximum, level))
            validated_ranges[level] = {"min": minimum, "max": maximum}

        occupied.sort()
        for previous, current in zip(occupied, occupied[1:]):
            if current[0] <= previous[1]:
                raise ValueError(f"Ranges overlap for task {name}.")

        validated.append({"name": name, "ranges": validated_ranges})
    return validated


def convert_raw_score(task, raw_score):
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        raise ValueError("Raw score must be a whole number.")
    if score < 0:
        raise ValueError("Raw score cannot be negative.")

    for level in reversed(LEVEL_NAMES):
        score_range = task.get("ranges", {}).get(level, {})
        minimum = int(score_range.get("min", 0))
        maximum = int(score_range.get("max", -1))
        if minimum <= score <= maximum:
            return {"level": level, "points": int(level.rsplit(" ", 1)[1])}
    raise ValueError(f"Raw score {score} does not match a configured level range.")


def task_score_bounds(task):
    ranges = task.get("ranges", {}).values()
    minima = [int(score_range["min"]) for score_range in ranges]
    maxima = [int(score_range["max"]) for score_range in ranges]
    return min(minima), max(maxima)