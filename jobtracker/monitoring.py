"""Numbers for the monitoring page: is the live model still doing well?

- usage:        predictions per day, how many got a user correction, odd inputs
- live metric:  the model's error on each NEW week of collected posts. Only posts published
                after the model was created count, so this never touches the frozen test set.
"""
import pandas as pd

from jobtracker.data import load_vacancies, week_start
from jobtracker.metrics import evaluate
from jobtracker.models import level_word, years_required
from jobtracker.predict import IT_HINTS, LOGGED_CHARS


def usage(conn, days=30):
    log = pd.read_sql("SELECT time, input, label FROM prediction_log", conn)
    if log.empty:
        return {"total": 0, "per_day": [], "labelled": 0, "odd": {}}
    per_day = log["time"].str[:10].value_counts().sort_index().tail(days)   # Tashkent days
    texts = log["input"]
    odd = {
        "does not look like an IT job": int((~texts.str.contains(IT_HINTS)).sum()),
        "no level word and no years": int(sum(level_word(t.lower()) is None and
                                              years_required(t) is None for t in texts)),
        f"very long (cut to {LOGGED_CHARS} chars in the log)": int((texts.str.len() >= LOGGED_CHARS).sum()),
    }
    return {"total": len(log), "per_day": list(per_day.items()),
            "labelled": int(log["label"].notna().sum()), "odd": odd}


def live_metric(conn, predictor, created):
    """One row per new week: posts, level macro F1, salary MAE of the live model."""
    df = load_vacancies(conn)
    df = df[df["posted_at"] > pd.Timestamp(created).tz_convert("UTC")]
    rows = []
    for start, week in df.groupby(week_start(df["posted_at"])):
        s = evaluate(predictor.level_model, predictor.salary_model, week)
        rows.append({"week": start.strftime("%d %b %Y"), "posts": len(week),
                     "level_f1": None if s["level_macro_f1"] is None else round(s["level_macro_f1"], 3),
                     "salary_mae": None if s["salary_mae"] is None else round(s["salary_mae"])})
    return rows
