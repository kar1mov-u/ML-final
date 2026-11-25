"""Load the vacancies from the database and apply the fixed date split.

One row = one unique vacancy (the first post of each duplicate group), so reposts can never
end up on both sides of the split.
"""
import pandas as pd

from jobtracker.config import TEST_START

# The brief asks for three levels. The LLM also finds "intern" and "lead";
# we merge them into the nearest of the three (documented label rule).
LEVEL_MAP = {"intern": "junior", "junior": "junior", "middle": "middle",
             "senior": "senior", "lead": "senior"}
LEVELS = ["junior", "middle", "senior"]


def load_vacancies(conn) -> pd.DataFrame:
    """All extracted IT job posts, oldest first, with a `split` column (train / test)."""
    df = pd.read_sql(
        """SELECT r.id, r.channel, r.posted_at, r.text,
                  v.title, v.level, v.salary_usd, v.skills
           FROM raw_posts r
           JOIN vacancies v ON v.raw_id = r.id
           WHERE v.is_job_post = 1 AND v.is_it_job = 1
             AND (r.dup_group IS NULL OR r.dup_group = r.id)
           ORDER BY r.posted_at""",
        conn,
    )
    df["posted_at"] = pd.to_datetime(df["posted_at"], utc=True)
    df["level"] = df["level"].map(LEVEL_MAP)          # "unknown" becomes NaN
    df["split"] = "train"
    df.loc[df["posted_at"] >= pd.Timestamp(TEST_START, tz="UTC"), "split"] = "test"
    return df


def level_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for the level model: level known."""
    return df[df["level"].notna()]


def salary_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Rows usable for the salary model: the post states a salary (see salary.py)."""
    return df[df["salary_usd"].notna()]


def week_start(posted_at: pd.Series) -> pd.Series:
    """Monday of each post's week (for per-week counts and the live metric)."""
    return posted_at.dt.tz_localize(None).dt.to_period("W").dt.start_time
