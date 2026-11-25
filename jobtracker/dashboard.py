"""Numbers for the weekly market dashboard: counts and medians only, no model involved."""
import json
from collections import Counter

import pandas as pd

from jobtracker.data import LEVELS, load_vacancies, week_start

WEEKS = 12          # the dashboard looks at the last 12 weeks of posts


def market_stats(conn):
    df = load_vacancies(conn)
    since = df["posted_at"].max() - pd.Timedelta(weeks=WEEKS)
    df = df[df["posted_at"] > since]

    per_week = week_start(df["posted_at"]).value_counts().sort_index()
    skills = Counter(s for row in df["skills"] for s in json.loads(row or "[]"))
    by_level = (df.dropna(subset=["salary_usd", "level"]).groupby("level")["salary_usd"]
                .agg(["count", "median"]).reindex(LEVELS).dropna())
    return {
        "since": since.strftime("%d %b %Y"),
        "posts": len(df),
        "per_week": [(d.strftime("%d %b"), int(n)) for d, n in per_week.items()],
        "top_skills": skills.most_common(15),
        "salary_by_level": [(lvl, int(r["count"]), int(r["median"])) for lvl, r in by_level.iterrows()],
    }
