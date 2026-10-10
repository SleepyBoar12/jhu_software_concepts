
CREATE TABLE IF NOT EXISTS applicants (
    p_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    program TEXT NOT NULL,
    comments TEXT,
    date_added DATE NOT NULL,
    url TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL,
    term TEXT,
    us_or_international TEXT,
    gpa DOUBLE PRECISION,
    gre DOUBLE PRECISION,
    gre_v DOUBLE PRECISION,
    gre_aw DOUBLE PRECISION,
    degree TEXT,
    llm_generated_program TEXT,
    llm_generated_university TEXT
);
