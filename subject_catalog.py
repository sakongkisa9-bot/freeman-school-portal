"""Subject catalog: full names with editable short forms, per school level."""

# Catalog groups. "pp" feeds both the pp1 and pp2 config sections.
CATALOG_GROUPS = [
    ("playgroup", "Playgroup", ["playgroup"], 4),
    ("pp", "Pre-Primary (PP1 & PP2)", ["pp1", "pp2"], 5),
    ("lower", "Lower Primary (Grade 1 - 3)", ["lower"], 7),
    ("primary", "Upper Primary (Grade 4 - 6)", ["primary"], 8),
    ("jss", "Junior School (Grade 7 - 9)", ["jss"], 9),
]

DEFAULT_CATALOG = {
    "playgroup": [
        ("Language and Social Activities", "LANG"),
        ("Mathematical and Sorting Activities", "MATH"),
        ("Environmental and Health Activities", "ENV"),
        ("Psychomotor and Creative Activities", "CREAT"),
    ],
    "pp": [
        ("Language Activities", "LANG"),
        ("Mathematical Activities", "MATH"),
        ("Environmental Activities", "ENV"),
        ("Psychomotor and Creative Activities", "CREAT"),
        ("Religious Education Activities", "RE"),
    ],
    "lower": [
        ("English Language", "ENG"),
        ("Kiswahili Language / Kenya Sign Language", "KISW"),
        ("Mathematics", "MATH"),
        ("Environmental Activities", "ENV"),
        ("Creative Activities", "CREAT"),
        ("Religious Education", "CRE"),
        ("Indigenous Language / Literacy Activities", "LIT"),
    ],
    "primary": [
        ("English", "ENG"),
        ("Kiswahili", "KISW"),
        ("Mathematics", "MATH"),
        ("Science and Technology", "SCI"),
        ("Agriculture and Nutrition", "AGRI"),
        ("Social Studies", "SST"),
        ("Creative Arts", "ARTS"),
        ("Religious Education", "CRE"),
    ],
    "jss": [
        ("Mathematics", "MATH"),
        ("English", "ENG"),
        ("Kiswahili / Kenya Sign Language", "KISW"),
        ("Integrated Science", "INT SCI"),
        ("Pre-Technical Studies", "PRE-TECH"),
        ("Social Studies", "SST"),
        ("Agriculture and Nutrition", "AGRI"),
        ("Creative Arts and Sports", "C/A"),
        ("Religious Education", "CRE"),
    ],
}


def _entry(name, short, selected=False, custom=False):
    return {"name": name, "short": short, "selected": selected, "custom": custom}


def build_catalog(config):
    """Return the school's catalog, seeding it from older `subjects` lists on first use."""
    saved = config.get("subject_catalog")
    if isinstance(saved, dict) and saved:
        catalog = {}
        for key, _, _, _ in CATALOG_GROUPS:
            items = saved.get(key)
            if items is None:
                items = [_entry(n, s) for n, s in DEFAULT_CATALOG[key]]
            catalog[key] = [dict(item) for item in items]
        return catalog

    legacy = config.get("subjects", {}) or {}
    catalog = {}
    for key, _, sections, _ in CATALOG_GROUPS:
        used = []
        for section in sections:
            for short in legacy.get(section, []):
                if short not in used:
                    used.append(short)
        items = [_entry(n, s, selected=s in used) for n, s in DEFAULT_CATALOG[key]]
        known = {item["short"] for item in items}
        for short in used:
            if short not in known:
                items.append(_entry(short, short, selected=True, custom=True))
        catalog[key] = items
    return catalog


def config_updates(catalog):
    """Config keys to save: the catalog, short-form lists per section and the short->full map."""
    subjects, names = {}, {}
    for key, _, sections, _ in CATALOG_GROUPS:
        chosen = [item for item in catalog.get(key, []) if item["selected"] and item["short"]]
        for section in sections:
            subjects[section] = [item["short"] for item in chosen]
            names[section] = {item["short"]: item["name"] for item in chosen}
    return {"subject_catalog": catalog, "subjects": subjects, "subject_names": names}


def all_full_names(subject_names):
    """Sorted unique full names across all sections of a `subject_names` mapping."""
    found = set()
    for mapping in (subject_names or {}).values():
        found.update(name for name in mapping.values() if name)
    return sorted(found)
