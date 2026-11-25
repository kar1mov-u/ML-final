"""SQLite database: schema, connection, and the one way posts get in.

Tables
- raw_posts       one row per collected post (personal data already removed)
- vacancies       one row per raw post after LLM extraction (labels + fields)
- prediction_log  one row per prediction served by the app (handbook minimum columns)
- hh_meta         hh.uz's own structured fields for hh vacancies (salary, experience, skills)
- hh_skipped      hh.uz vacancy ids we checked and rejected as non-IT (never fetched again)
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from jobtracker.clean import scrub_pii, text_hash
from jobtracker.config import DB_PATH, TASHKENT

SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_posts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT NOT NULL,             -- 'telegram' / 'hh'
    channel       TEXT NOT NULL,             -- e.g. 'uzdev_jobs', 'hh.uz'
    msg_id        INTEGER NOT NULL,          -- message id in the channel / hh vacancy id
    posted_at     TEXT NOT NULL,             -- ISO time, UTC
    text          TEXT NOT NULL,             -- PII-scrubbed post text
    text_hash     TEXT NOT NULL,             -- hash of normalised text (exact-duplicate check)
    dup_group     INTEGER,                   -- id of the first post in its duplicate group
    collected_at  TEXT NOT NULL,
    UNIQUE (source, channel, msg_id)
);

CREATE TABLE IF NOT EXISTS vacancies (
    raw_id          INTEGER PRIMARY KEY REFERENCES raw_posts(id),
    is_job_post     INTEGER,
    is_it_job       INTEGER,
    title           TEXT,
    level           TEXT,                    -- intern / junior / middle / senior / lead / unknown
    salary_min      REAL,                    -- as written in the post
    salary_max      REAL,
    currency        TEXT,                    -- USD / UZS / RUB / EUR / null
    salary_period   TEXT,                    -- month / year / hour / null
    salary_usd      REAL,                    -- normalised target, USD per month (see salary.py)
    skills          TEXT,                    -- JSON list
    language        TEXT,                    -- uz / ru / en / mixed
    extracted_json  TEXT NOT NULL,           -- full LLM output, for audits
    llm_model       TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    extracted_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prediction_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    time           TEXT NOT NULL,            -- Tashkent time
    input          TEXT NOT NULL,            -- anonymised input, shortened
    prediction     TEXT NOT NULL,            -- JSON: level + salary
    confidence     REAL,
    model_version  TEXT NOT NULL,
    label          TEXT,                     -- filled later (user correction)
    label_time     TEXT
);

CREATE TABLE IF NOT EXISTS hh_meta (
    vacancy_id     INTEGER PRIMARY KEY,      -- = raw_posts.msg_id where source = 'hh'
    salary_from    REAL,                     -- hh's structured salary fields, as published
    salary_to      REAL,
    currency       TEXT,
    salary_period  TEXT,
    gross          INTEGER,                  -- 1 = before tax, 0 = after tax, NULL = not stated
    salary_text    TEXT,
    experience     TEXT,                     -- hh's experience bucket, e.g. "1–3 года"
    skills         TEXT,                     -- JSON list of hh key skills
    collected_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hh_skipped (
    vacancy_id     INTEGER PRIMARY KEY,
    title          TEXT,
    checked_at     TEXT NOT NULL
);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open the database (creating tables if needed). Rows behave like dicts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def tashkent_now() -> str:
    return datetime.now(TASHKENT).isoformat(timespec="seconds")


def insert_post(conn, source: str, channel: str, msg_id: int, posted_at: str, text: str) -> bool:
    """Store one collected post; True if it was new. Every collector goes through here, and the
    text is scrubbed here, so personal data can never reach the database."""
    text = scrub_pii(text)
    cur = conn.execute(
        """INSERT OR IGNORE INTO raw_posts
           (source, channel, msg_id, posted_at, text, text_hash, collected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (source, channel, msg_id, posted_at, text, text_hash(text), utc_now()),
    )
    return cur.rowcount == 1
