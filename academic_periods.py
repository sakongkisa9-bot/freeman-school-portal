TERMS = ("Term 1", "Term 2", "Term 3")


def available_terms(selected_year, current_year, current_term):
    selected = None if selected_year in (None, "", "-") else str(selected_year)
    current = None if current_year in (None, "", "-") else str(current_year)
    if selected is not None and current is not None and selected != current:
        return TERMS
    try:
        return TERMS[: TERMS.index(current_term) + 1]
    except ValueError:
        return TERMS[:1]