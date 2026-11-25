"""The metrics, defined once and used everywhere: CV (train.py), the one test score (train.py
--final), the promotion gate (retrain.py) and the live metric (monitoring page)."""
import numpy as np
from sklearn.metrics import f1_score, make_scorer, mean_absolute_error

from jobtracker.data import level_rows, salary_rows


def overestimated_30(y_true, y_pred):
    """Cost of mistakes from the brief: share of posts where we promise >30% too much."""
    return float(np.mean(np.asarray(y_pred) > 1.3 * np.asarray(y_true)))


def macro_f1(y_true, y_pred):
    return f1_score(y_true, y_pred, average="macro", zero_division=0)


LEVEL_SCORING = {"macro_f1": make_scorer(macro_f1)}
SALARY_SCORING = {"mae": make_scorer(mean_absolute_error), "over30": make_scorer(overestimated_30)}


def evaluate(level_model, salary_model, df):
    """Score both models on the vacancies in df. A metric is None when df has no rows for it."""
    lv, sal = level_rows(df), salary_rows(df)
    scores = {"level_macro_f1": None, "salary_mae": None, "salary_over30": None,
              "rows": {"level": len(lv), "salary": len(sal)}}
    if len(lv):
        scores["level_macro_f1"] = round(macro_f1(lv["level"], level_model.predict(lv["text"])), 4)
    if len(sal):
        pred = salary_model.predict(sal["text"])
        scores["salary_mae"] = round(mean_absolute_error(sal["salary_usd"], pred), 2)
        scores["salary_over30"] = round(overestimated_30(sal["salary_usd"], pred), 4)
    return scores
