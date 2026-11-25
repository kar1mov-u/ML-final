"""Train a new candidate on new data and promote it ONLY if it beats the live model.

    python retrain.py                    # candidate uses the same model types as the live model
    python retrain.py --level logistic_regression_hints --salary linear_ridge_hints_log

The promotion gate
1. held-out data = the latest week of collected posts (the newest 7 days)
2. the candidate learns from everything older than that week, plus the corrections users sent
   through the app (prediction_log.label): this is the feedback loop
3. live model and candidate are scored on the SAME held-out week
4. the candidate is promoted (models/LIVE) only if it is at least as good on both targets and
   better on at least one; otherwise the live model stays
The candidate files and the decision are saved either way (docs/promotion_log.md).
"""
import argparse
import json

import pandas as pd

from jobtracker import registry
from jobtracker.config import ROOT
from jobtracker.data import level_rows, load_vacancies, salary_rows
from jobtracker.db import connect, tashkent_now
from jobtracker.metrics import evaluate
from jobtracker.models import level_candidates, salary_candidates
from jobtracker.predict import Predictor

PROMOTION_LOG = ROOT / "docs" / "promotion_log.md"


def feedback_rows(conn):
    """User corrections from the app, as extra training rows (text, level, salary_usd)."""
    log = pd.read_sql("SELECT input, label FROM prediction_log WHERE label IS NOT NULL", conn)
    labels = [json.loads(x) for x in log["label"]]
    return pd.DataFrame({"text": log["input"],
                         "level": [lab.get("level") for lab in labels],
                         "salary_usd": [lab.get("salary_usd") for lab in labels]})


def beats(new, old):
    """The gate: not worse on either target, better on at least one."""
    f1_new, f1_old, mae_new, mae_old = (new["level_macro_f1"], old["level_macro_f1"],
                                        new["salary_mae"], old["salary_mae"])
    return f1_new >= f1_old and mae_new <= mae_old and (f1_new > f1_old or mae_new < mae_old)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", help="level model for the candidate (default: same as live)")
    parser.add_argument("--salary", help="salary model for the candidate (default: same as live)")
    args = parser.parse_args(argv)

    if not registry.released():
        # before the release, the newest weeks ARE the frozen test set: do not touch them
        raise SystemExit("Release v1 first (python train.py --version v1 --final). "
                         "Before that, the newest weeks belong to the test set.")

    conn = connect()
    live = Predictor()
    level_name = args.level or live.meta["level_model"]
    salary_name = args.salary or live.meta["salary_model"]

    # 1. held-out = latest week; 2. train on everything before it + user feedback
    df = load_vacancies(conn)
    week_start = df["posted_at"].max() - pd.Timedelta(days=7)
    week, older = df[df["posted_at"] > week_start], df[df["posted_at"] <= week_start]
    extra = feedback_rows(conn)
    train_level = pd.concat([level_rows(older)[["text", "level"]], extra.dropna(subset=["level"])])
    train_salary = pd.concat([salary_rows(older)[["text", "salary_usd"]],
                              extra.dropna(subset=["salary_usd"])])
    print(f"held-out week from {week_start:%Y-%m-%d}: {len(week)} posts; training rows: "
          f"level {len(train_level)}, salary {len(train_salary)} (incl. {len(extra)} user corrections)")

    level_model = level_candidates()[level_name].fit(train_level["text"], train_level["level"])
    salary_model = salary_candidates()[salary_name].fit(train_salary["text"], train_salary["salary_usd"])

    # 3. same held-out week for both
    old = evaluate(live.level_model, live.salary_model, week)
    new = evaluate(level_model, salary_model, week)
    promoted = beats(new, old)

    # 4. save the candidate and the decision either way
    version = registry.next_version()
    created = tashkent_now()
    registry.save(version, {"level": level_model, "salary": salary_model}, {
        "created": created,
        "level_model": level_name, "salary_model": salary_name,
        "data": {"train_level_rows": len(train_level), "train_salary_rows": len(train_salary),
                 "user_corrections": len(extra), "heldout_week_start": f"{week_start:%Y-%m-%d}",
                 "heldout_posts": len(week)},
        "cv": live.meta["cv"],                       # model types unchanged unless --level/--salary
        "salary_cv_mae": live.meta["salary_cv_mae"],
        "test": None,
        "gate": {"against": live.version, "live": old, "candidate": new, "promoted": promoted},
    })
    print(f"live {live.version}: {old}\ncandidate {version}: {new}")
    if promoted:
        registry.set_live(version)
        print(f"PROMOTED: models/LIVE -> {version} (the app switches on its next request).")
    else:
        print(f"NOT promoted: {live.version} stays live.")

    with open(PROMOTION_LOG, "a") as log:
        log.write(f"| {created[:10]} | {live.version} | {version} | {week_start:%Y-%m-%d} "
                  f"({len(week)} posts) | {old['level_macro_f1']} / {old['salary_mae']} | "
                  f"{new['level_macro_f1']} / {new['salary_mae']} | {'yes' if promoted else 'no'} |\n")


if __name__ == "__main__":
    main()
