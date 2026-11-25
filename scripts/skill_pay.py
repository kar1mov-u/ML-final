"""Which skills go with higher pay? (advanced task from the brief)

    python -m scripts.skill_pay          # writes docs/skills_and_pay.md

A linear regression learns log(salary) from which skills a post lists, plus its level.
Each skill's coefficient says: posts that list this skill pay about X% more or less than
similar posts (same level, same other skills) that don't. Train part only.
This is CORRELATION, not cause: learning a skill does not by itself raise a salary
(e.g. Go may simply be asked for by richer companies).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import MultiLabelBinarizer

from jobtracker.data import load_vacancies, salary_rows
from jobtracker.db import connect

MIN_POSTS = 30          # skills in fewer posts are too noisy to say anything about


def main():
    df = load_vacancies(connect())
    df = salary_rows(df[df["split"] == "train"])
    skills = df["skills"].apply(lambda s: json.loads(s or "[]"))

    counts = pd.Series([s for row in skills for s in row]).value_counts()
    common = sorted(counts[counts >= MIN_POSTS].index)
    skill_matrix = MultiLabelBinarizer(classes=common).fit_transform(
        skills.apply(lambda row: [s for s in row if s in common]))
    level = pd.get_dummies(df["level"].fillna("unknown")).to_numpy(dtype=float)  # control

    X = np.hstack([skill_matrix, level])
    model = Ridge(alpha=1.0).fit(X, np.log(df["salary_usd"]))
    effect = pd.Series(np.exp(model.coef_[:len(common)]) - 1, index=common)   # % difference

    table = pd.DataFrame({"posts": counts[common], "pay difference": effect}).sort_values(
        "pay difference", ascending=False)
    lines = [
        "# Skills that go with higher pay",
        "",
        f"Linear regression on log(salary), {len(df)} train posts with a salary, controlling for "
        f"level. Skills in at least {MIN_POSTS} posts. **Correlation, not cause.**",
        "",
        "| Skill | Posts | Pay vs. similar posts without it |",
        "|---|---|---|",
    ]
    for skill, row in table.iterrows():
        lines.append(f"| {skill} | {int(row['posts'])} | {row['pay difference']:+.0%} |")
    Path("docs/skills_and_pay.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:6] + lines[6:16] + ["..."] + lines[-5:]))


if __name__ == "__main__":
    main()
