-- ──────────────────────────────────────────────────────────────
--  Court-Listener docket pipeline  •  Relational schema v0.3
-- ──────────────────────────────────────────────────────────────
--  Tables:
--    cases       – one row per docket / lawsuit
--    filings     – one row per docket entry (documents, orders…)
--    parties     – one row per party / attorney
--    outcomes    – one row per case outcome / disposition
--  Mat-views:
--    judge_win_rates – yearly win rate for each judge
-- ----------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS public;
SET search_path = public;

-- ─── core docket information ──────────────────────────────────
CREATE TABLE IF NOT EXISTS cases (
    case_id        BIGINT PRIMARY KEY,               -- stable CL docket ID
    url            TEXT            NOT NULL,         -- v4 API URL for the docket
    court_slug     TEXT            NOT NULL,         -- e.g. 'dcd'
    docket_number  TEXT,                             -- court-assigned number
    filing_date    DATE,                             -- date_filed
    closing_date   DATE,                             -- date_closed (if any)
    nature_of_suit TEXT,                             -- NOS code
    cause          TEXT,                             -- 'cause_of_action'
    case_name      TEXT,                             -- short caption
    judge_id       BIGINT                            -- add later if/when you fetch judge data
);

CREATE INDEX IF NOT EXISTS idx_cases_court_date
    ON cases (court_slug, filing_date);

-- ─── individual docket entries ────────────────────────────────
CREATE TABLE IF NOT EXISTS filings (
    filing_id      BIGINT PRIMARY KEY,               -- CL entry ID
    case_id        BIGINT REFERENCES cases ON DELETE CASCADE,
    seq_no         INT,                              -- docket entry number
    entry_date     DATE,
    category       TEXT,                             -- 'entry_type'
    description    TEXT
);

CREATE INDEX IF NOT EXISTS idx_filings_case ON filings (case_id);
CREATE INDEX IF NOT EXISTS idx_filings_date ON filings (entry_date);

-- ─── parties / attorneys ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS parties (
    party_id       BIGINT PRIMARY KEY,               -- CL party ID
    case_id        BIGINT REFERENCES cases ON DELETE CASCADE,
    name           TEXT,
    party_type     TEXT,                             -- 'person', 'company', etc.
    role           TEXT                              -- 'plaintiff', 'defendant', …
);

CREATE INDEX IF NOT EXISTS idx_parties_case ON parties (case_id);

-- ─── outcomes / dispositions ─────────────────────────────────
CREATE TABLE IF NOT EXISTS outcomes (
    case_id        BIGINT PRIMARY KEY REFERENCES cases,
    outcome        TEXT,      -- 'winner', 'dismissed', 'settled', …
    disposition    TEXT,      -- free-text from CourtListener
    outcome_date   DATE,
    win_bool       BOOLEAN
);

-- populate / refresh the label column from `outcomes`

-- copy win_bool into the cases table (add the column on first run)
ALTER TABLE cases
    ADD COLUMN IF NOT EXISTS outcome_win BOOLEAN;

UPDATE cases AS c
SET    outcome_win = o.win_bool
FROM   outcomes o
WHERE  o.case_id = c.case_id
  AND  c.outcome_win IS DISTINCT FROM o.win_bool;

-- ──────────────────────────────────────────────────────────────
--  Materialised view : judge_win_rates
--  (Yearly win-rate for each judge.  Uses judge_id once you add it.)
-- ──────────────────────────────────────────────────────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS judge_win_rates AS
WITH yearly AS (
    SELECT
        c.judge_id,                                    -- nullable for now
        EXTRACT(year FROM o.outcome_date)::INT AS filing_year,
        COUNT(*)                                    AS total_cases,
        SUM(CASE WHEN o.win_bool THEN 1 ELSE 0 END) AS wins
    FROM cases     c
    JOIN outcomes  o ON o.case_id = c.case_id
    WHERE o.outcome IS NOT NULL
    GROUP BY 1, 2
)
SELECT
    judge_id,
    filing_year,
    wins::FLOAT / NULLIF(total_cases,0) AS win_rate
FROM yearly;

CREATE INDEX IF NOT EXISTS idx_jwr_judge_year
    ON judge_win_rates (judge_id, filing_year);
