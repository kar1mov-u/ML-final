"""Model smoke test, input-check test and split test (handbook 'advanced': >= 3 tests)."""
import numpy as np

from jobtracker.data import load_vacancies
from jobtracker.db import connect
from jobtracker.models import KeywordLevelRule, level_candidates, salary_candidates
from jobtracker.predict import check_feedback, check_input

# a tiny fake data set: enough rows for TF-IDF (min_df=3) and kNN (10 neighbours)
TEXTS = ([f"Senior Python developer {i}, 5 years, Django, PostgreSQL, salary 3000$" for i in range(10)]
         + [f"Junior frontend developer {i}, React, no experience, 500$" for i in range(10)]
         + [f"Middle Java developer {i}, 2 years, Spring, 1500$" for i in range(10)])
LEVELS = ["senior"] * 10 + ["junior"] * 10 + ["middle"] * 10
SALARIES = [3000] * 10 + [500] * 10 + [1500] * 10


def test_every_candidate_trains_and_predicts():
    for name, pipe in level_candidates().items():
        pred = pipe.fit(TEXTS, LEVELS).predict(["Senior Python developer, Django"])
        assert pred[0] in {"junior", "middle", "senior"}, name
    for name, pipe in salary_candidates().items():
        pred = pipe.fit(TEXTS, SALARIES).predict(["Junior frontend developer, React"])
        assert np.isfinite(pred[0]), name


def test_keyword_level_rule():
    rule = KeywordLevelRule().fit(["x", "y"], ["middle", "middle"])
    assert list(rule.predict(["senior go developer", "3+ years of java", "something else"])) == \
        ["senior", "senior", "middle"]


def test_input_checks():
    assert check_input("")[0]                                   # empty
    assert check_input(None)[0]                                 # wrong type
    assert check_input("python dev")[0]                         # too short
    assert check_input("a " * 5000)[0]                          # too long
    assert check_input("Ищем бухгалтера в офис, опыт работы от двух лет, полный день")[1]  # not IT -> warning
    error, warning = check_input("We need a Python developer with Django and 2 years of experience")
    assert error is None and warning is None


def test_split_by_date(tmp_path):
    conn = connect(tmp_path / "t.db")
    for i, date in enumerate(["2026-08-31T23:00:00+00:00", "2026-09-01T00:00:00+00:00"]):
        conn.execute("INSERT INTO raw_posts (id, source, channel, msg_id, posted_at, text, text_hash,"
                     " dup_group, collected_at) VALUES (?, 'tg', 'c', ?, ?, 'text', 'h', ?, 'now')",
                     (i + 1, i + 1, date, i + 1))
        conn.execute("INSERT INTO vacancies (raw_id, is_job_post, is_it_job, level, salary_usd,"
                     " extracted_json, llm_model, prompt_version, extracted_at)"
                     " VALUES (?, 1, 1, 'lead', 1000, '{}', 'test', 'v0', 'now')", (i + 1,))
    df = load_vacancies(conn)
    assert list(df["split"]) == ["train", "test"]
    assert list(df["level"]) == ["senior", "senior"]            # lead merged into senior


def test_feedback_checks():
    assert check_feedback("senior", "1500") == (None, {"level": "senior", "salary_usd": 1500.0})
    assert check_feedback("", "") [0]                           # nothing sent
    assert check_feedback("boss", "")[0]                        # unknown level
    assert check_feedback("", "5")[0]                           # absurd salary
    assert check_feedback("", "abc")[0]                         # not a number
