"""Make the hand-labelling sheet: 100 random extracted posts, 50 for each partner.

    python -m scripts.label_sheet            # writes docs/labels/hand_labels.csv

The sheet does NOT show what the LLM said (blind labelling, so we are not influenced).
Posts come from the TRAIN period only: we never look at the test posts.
Fill the empty columns, then run: python -m scripts.label_agreement

How to fill
    is_it_job : 1 or 0
    level     : junior / middle / senior / unknown   (rule: named level wins, else years:
                <1 junior, 1-3 middle, 3+ senior, else unknown; intern=junior, lead=senior)
    salary_usd: USD per month (range -> midpoint, "from X" -> X; 12 500 UZS = 1 USD), empty if none
"""
import argparse
from pathlib import Path

import pandas as pd

from jobtracker.config import TEST_START
from jobtracker.db import connect

OUT = Path("docs/labels/hand_labels.csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--n", type=int, default=100)
    args = parser.parse_args()
    if OUT.exists():
        raise SystemExit(f"{OUT} already exists; delete it only if nobody has started labelling.")

    df = pd.read_sql(
        """SELECT r.id AS raw_id, r.text FROM raw_posts r JOIN vacancies v ON v.raw_id = r.id
           WHERE r.posted_at < ?""",
        connect(), params=(TEST_START,),
    )
    sample = df.sample(n=min(args.n, len(df)), random_state=42).reset_index(drop=True)
    sample.insert(0, "labeller", ["A" if i < len(sample) / 2 else "B" for i in range(len(sample))])
    for col in ["is_it_job", "level", "salary_usd", "note"]:
        sample[col] = ""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT, index=False)
    print(f"wrote {len(sample)} posts to {OUT}")


if __name__ == "__main__":
    main()
