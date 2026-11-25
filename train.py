"""Rebuild the models from the database in one command.

    python train.py                  # compare all models with CV, save the best as the next version
    python train.py --cv-only        # only print the CV comparison (for the experiment log)
    python train.py --version v0 --level smart_keyword_rule --salary smart_keyword_median
                                     # save chosen models instead of the CV winners
    python train.py --version v1 --final
                                     # RELEASE ONLY: also score the test set, once

Steps
1. load unique IT vacancies from the DB, split by date (config.TEST_START)
2. on the TRAIN part only: time-ordered 5-fold cross-validation for every candidate
3. refit the chosen candidates on all train rows
4. save models/model_vN.joblib + model_vN.json (jobtracker/registry.py)
The test rows are never touched unless --final is given, and --final works only once.
"""
import argparse

from sklearn.model_selection import TimeSeriesSplit, cross_validate

from jobtracker import registry
from jobtracker.config import PROMPT_VERSION, TEST_START
from jobtracker.data import level_rows, load_vacancies, salary_rows
from jobtracker.db import connect, tashkent_now
from jobtracker.metrics import LEVEL_SCORING, SALARY_SCORING, evaluate
from jobtracker.models import level_candidates, salary_candidates

CV = TimeSeriesSplit(n_splits=5)   # each fold: train on older posts, validate on the next ones


def cross_validate_all(candidates, X, y, scoring):
    """{name: {metric: mean CV score}} for every candidate."""
    results = {}
    for name, pipe in candidates.items():
        cv = cross_validate(pipe, X, y, cv=CV, scoring=scoring)
        results[name] = {m: round(float(cv[f"test_{m}"].mean()), 4) for m in scoring}
    return results


def print_table(title, results):
    metrics = list(next(iter(results.values())))
    print(f"\n{title}\n  {'model':26}" + "".join(f"{m:>10}" for m in metrics))
    for name, scores in results.items():
        print(f"  {name:26}" + "".join(f"{scores[m]:>10}" for m in metrics))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", help="e.g. v0, v1 (default: next free number)")
    parser.add_argument("--level", help="level model to save (default: best macro F1)")
    parser.add_argument("--salary", help="salary model to save (default: lowest MAE)")
    parser.add_argument("--final", action="store_true", help="score the test set (release only)")
    parser.add_argument("--cv-only", action="store_true", help="compare models, save nothing")
    args = parser.parse_args(argv)

    version = args.version or registry.next_version()
    if registry.exists(version):
        raise SystemExit(f"model_{version} already exists: versions are never overwritten.")
    if args.final and registry.released():
        raise SystemExit(f"The test set was already used in {registry.released()}. "
                         "It may be used only once (handbook rule).")

    # 1. data
    df = load_vacancies(connect())
    train, test = df[df["split"] == "train"], df[df["split"] == "test"]
    lv, sal = level_rows(train), salary_rows(train)
    print(f"{len(df)} IT vacancies: {len(train)} train / {len(test)} test (test from {TEST_START})")
    print(f"train rows with level: {len(lv)}, with salary: {len(sal)}")

    # 2. cross-validation on train only
    level_cv = cross_validate_all(level_candidates(), lv["text"], lv["level"], LEVEL_SCORING)
    salary_cv = cross_validate_all(salary_candidates(), sal["text"], sal["salary_usd"], SALARY_SCORING)
    print_table("LEVEL (macro F1, higher is better)", level_cv)
    print_table("SALARY (MAE in USD and share overestimated >30%, lower is better)", salary_cv)
    if args.cv_only:
        return

    # 3. choose and refit on all train rows
    level_name = args.level or max(level_cv, key=lambda n: level_cv[n]["macro_f1"])
    salary_name = args.salary or min(salary_cv, key=lambda n: salary_cv[n]["mae"])
    level_model = level_candidates()[level_name].fit(lv["text"], lv["level"])
    salary_model = salary_candidates()[salary_name].fit(sal["text"], sal["salary_usd"])
    print(f"\nsaving {version}: level = {level_name}, salary = {salary_name}")

    # 4. (release only) the one and only test evaluation
    test_scores = evaluate(level_model, salary_model, test) if args.final else None
    if test_scores:
        print(f"TEST (computed once): {test_scores}")

    registry.save(version, {"level": level_model, "salary": salary_model}, {
        "created": tashkent_now(),
        "level_model": level_name,
        "salary_model": salary_name,
        "data": {
            "vacancies": len(df), "train": len(train), "test": len(test),
            "train_level_rows": len(lv), "train_salary_rows": len(sal),
            "first_post": str(df["posted_at"].min().date()) if len(df) else None,
            "test_start": TEST_START,
            "extraction_prompt": PROMPT_VERSION,
        },
        "cv": {"level": level_cv, "salary": salary_cv},
        "salary_cv_mae": salary_cv[salary_name]["mae"],     # the app shows "salary ± this"
        "test": test_scores,
    })
    print(f"wrote models/model_{version}.joblib and .json")
    if args.final:                      # the release becomes the model users get
        registry.set_live(version)
        print(f"models/LIVE -> {version}")


if __name__ == "__main__":
    main()
