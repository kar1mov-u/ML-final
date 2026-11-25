"""Error-analysis worksheet: the 20 worst predictions on VALIDATION data (never the test set).

    python -m scripts.worst_predictions --target salary --model smart_keyword_median
    python -m scripts.worst_predictions --target level  --model logistic_regression

How: the train part is ordered by date; the model learns on the oldest 80% and predicts the
newest 20% (validation). The 20 biggest mistakes go into docs/error_analysis_<target>.md.
Then fill the Cause column by hand (wrong label, missing feature, rare case, typo or outlier,
duplicate or leakage, other) and count the causes: the most common one decides the next step.
"""
import argparse
from pathlib import Path

import pandas as pd

from jobtracker.data import LEVELS, level_rows, load_vacancies, salary_rows
from jobtracker.db import connect
from jobtracker.models import level_candidates, salary_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", choices=["salary", "level"], required=True)
    parser.add_argument("--model", required=True, help="name from jobtracker/models.py")
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    df = load_vacancies(connect())
    train = df[df["split"] == "train"]                         # the test part is never used
    if args.target == "salary":
        rows, label, pipe = salary_rows(train), "salary_usd", salary_candidates()[args.model]
    else:
        rows, label, pipe = level_rows(train), "level", level_candidates()[args.model]

    cut = int(len(rows) * 0.8)                                 # rows are already oldest first
    fit_part, valid = rows.iloc[:cut], rows.iloc[cut:].copy()
    pipe.fit(fit_part["text"], fit_part[label])
    valid["predicted"] = pipe.predict(valid["text"])

    if args.target == "salary":
        valid["error"] = (valid["predicted"] - valid[label]).round(0)       # + = overestimate
        worst = valid.reindex(valid["error"].abs().sort_values(ascending=False).index)
    else:
        # how many levels apart (junior vs senior = 2 is worse than junior vs middle = 1)
        rank = {lvl: i for i, lvl in enumerate(LEVELS)}
        valid["error"] = (valid["predicted"].map(rank) - valid[label].map(rank)).abs()
        worst = valid[valid["error"] > 0].sort_values("error", ascending=False)
    worst = worst.head(args.n)

    lines = [
        f"# Error analysis: {args.target} ({args.model})",
        "",
        f"Validation = newest 20% of the train part ({len(valid)} posts, from "
        f"{valid['posted_at'].min():%Y-%m-%d}). Fit on the older {len(fit_part)} posts.",
        "Causes: wrong label, missing feature, rare case, typo or outlier, duplicate or leakage, other.",
        "",
        "| Example ID | True | Predicted | Error | Cause | Note | Post (start) |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in worst.iterrows():
        true, pred = r[label], r["predicted"]
        if args.target == "salary":
            true, pred = f"{true:.0f}", f"{pred:.0f}"
        start = " ".join(r["text"].split())[:90].replace("|", "/")
        lines.append(f"| {r['id']} | {true} | {pred} | {r['error']} |  |  | {start} |")
    lines += ["", "## Cause counts", "| Cause | Count |", "|---|---|", "|  |  |", "",
              "**Decision:** (fix the data or change the model, and why)"]

    out = Path(f"docs/error_analysis_{args.target}.md")
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(worst)} rows)")


if __name__ == "__main__":
    main()
