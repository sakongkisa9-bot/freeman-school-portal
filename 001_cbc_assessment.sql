CREATE TABLE IF NOT EXISTS cbc_learning_areas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL,
    grade TEXT NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (school_id, grade, name)
);

CREATE TABLE IF NOT EXISTS cbc_strands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    learning_area_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (learning_area_id, name),
    FOREIGN KEY (learning_area_id) REFERENCES cbc_learning_areas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cbc_sub_strands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strand_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    UNIQUE (strand_id, name),
    FOREIGN KEY (strand_id) REFERENCES cbc_strands(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cbc_rubric_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL,
    grade TEXT NOT NULL,
    assessment_number TEXT NOT NULL,
    academic_year INTEGER NOT NULL,
    term TEXT NOT NULL,
    assessment_type TEXT NOT NULL CHECK (assessment_type IN ('Formative', 'Localized Summative')),
    sub_strand_id INTEGER NOT NULL,
    rating TEXT NOT NULL CHECK (rating IN ('1', '2', '3', '4', 'AB')),
    evidence TEXT,
    teacher_code TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE (school_id, grade, assessment_number, academic_year, term, assessment_type, sub_strand_id),
    FOREIGN KEY (sub_strand_id) REFERENCES cbc_sub_strands(id)
);

CREATE TABLE IF NOT EXISTS cbc_milestone_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL,
    grade TEXT NOT NULL CHECK (grade IN ('Grade 6', 'Grade 9')),
    assessment_number TEXT NOT NULL,
    academic_year INTEGER NOT NULL,
    sba_percent REAL NOT NULL CHECK (sba_percent BETWEEN 0 AND 100),
    grade7_sba_percent REAL CHECK (grade7_sba_percent BETWEEN 0 AND 100),
    grade8_sba_percent REAL CHECK (grade8_sba_percent BETWEEN 0 AND 100),
    national_percent REAL NOT NULL CHECK (national_percent BETWEEN 0 AND 100),
    sba_weight REAL NOT NULL DEFAULT 0.4 CHECK (sba_weight = 0.4),
    national_weight REAL NOT NULL DEFAULT 0.6 CHECK (national_weight = 0.6),
    weighted_result REAL NOT NULL CHECK (weighted_result BETWEEN 0 AND 100),
    updated_at TEXT NOT NULL,
    UNIQUE (school_id, grade, assessment_number, academic_year)
);

CREATE INDEX IF NOT EXISTS idx_cbc_rubric_assessment
ON cbc_rubric_scores (school_id, grade, assessment_number, academic_year, term);