"""Compare our hand labels with the LLM labels (how good are the labels we train on?).

    python -m scripts.label_agreement

Reads docs/labels/hand_labels.csv (filled by hand) and prints agreement per field.
Put the numbers in the report, and use the disagreements in error analysis ("wrong label").
"""
import pandas as pd

from jobtracker.data import LEVEL_MAP
from jobtracker.db import connect
from scripts.label_sheet import OUT


def main():
    hand = pd.read_csv(OUT)
    hand = hand[hand["is_it_job"].notna()]                    # only rows already labelled
    llm = pd.read_sql("SELECT raw_id, is_it_job, level, salary_usd FROM vacancies", connect())
    df = hand.merge(llm, on="raw_id", suffixes=("_hand", "_llm"))
    print(f"{len(df)} labelled posts")
    if df.empty:
        return

    it = (df["is_it_job_hand"].astype(int) == df["is_it_job_llm"]).mean()
    print(f"is_it_job agreement: {it:.0%}")

    llm_level = df["level_llm"].map(LEVEL_MAP).fillna("unknown")
    lv = (df["level_hand"].str.strip().str.lower() == llm_level).mean()
    print(f"level agreement:     {lv:.0%}")

    both = df.dropna(subset=["salary_usd_hand", "salary_usd_llm"])
    has_hand, has_llm = df["salary_usd_hand"].notna(), df["salary_usd_llm"].notna()
    print(f"salary found by both / hand only / LLM only: "
          f"{len(both)} / {(has_hand & ~has_llm).sum()} / {(~has_hand & has_llm).sum()}")
    if len(both):
        close = ((both["salary_usd_hand"] - both["salary_usd_llm"]).abs()
                 <= 0.05 * both["salary_usd_hand"]).mean()
        print(f"salary within 5% (when both found): {close:.0%}")

    print("\nLevel disagreements (for error analysis):")
    diff = df[df["level_hand"].str.strip().str.lower() != llm_level]
    for _, r in diff.iterrows():
        print(f"  post {r.raw_id}: hand={r.level_hand} llm={r.level_llm}")


if __name__ == "__main__":
    main()
