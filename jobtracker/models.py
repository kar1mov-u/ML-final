"""Every model we compare, each as ONE scikit-learn Pipeline that takes raw post text.

    raw text ──► clean (remove salary numbers) ──► features ──► model
    features = TF-IDF of words                   (plain models)
             = TF-IDF + 7 level hints            ("_hints" models: level words + years asked for)

The same Pipeline object is used for cross-validation, for the saved model file and inside the
app, so training and serving always prepare the text the same way.

Level (classification):  dummy, keyword rule (smart baseline), Naive Bayes, Logistic Regression
Salary (regression):     dummy, title-keyword median (smart baseline), Ridge, kNN, Decision tree

(Saved model files refer to clean_texts, LevelHints, KeywordLevelRule and KeywordSalaryMedian by
name: keep those names, or old model versions can no longer be loaded.)
"""
import re

import numpy as np
from sklearn.base import BaseEstimator, ClassifierMixin, RegressorMixin, TransformerMixin
from sklearn.compose import TransformedTargetRegressor
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.naive_bayes import MultinomialNB
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.tree import DecisionTreeRegressor

from jobtracker.clean import strip_salary


def clean_texts(texts):
    """Lower-case and remove salary amounts/currencies (leakage guard, see clean.py)."""
    return [strip_salary(str(t)).lower() for t in texts]


# --- level hints: the level word and the years of experience in a post ----------------------

LEVEL_WORDS = {
    "senior": r"\b(senior|сеньор|синьор|lead|лид|team ?lead|head of)\b",
    "middle": r"\b(middle|мидл)\b",
    "junior": r"\b(junior|джун\w*|intern|стажер\w*|стажёр\w*|amaliyotchi|trainee)\b",
}
# "3+ years", "от 2 лет", "2 yil" ...
YEARS = re.compile(r"(\d+(?:[.,]\d)?)\s*\+?\s*(?:years?|yrs?|год\w*|лет|yil)", re.IGNORECASE)


def level_word(text):
    """The first level named in the text ("senior", "junior", ...), or None."""
    return next((lvl for lvl, pattern in LEVEL_WORDS.items() if re.search(pattern, text)), None)


def years_required(text):
    """Years of experience asked for ("3+ years" -> 3.0), or None."""
    match = YEARS.search(text)
    return float(match.group(1).replace(",", ".")) if match else None


def level_from_years(years):
    return "junior" if years < 1 else "middle" if years < 3 else "senior"


class LevelHints(BaseEstimator, TransformerMixin):
    """7 numbers (0/1) per text, used next to TF-IDF: mentions senior / middle / junior
    (several can be 1, e.g. "Middle/Senior"); asks for no years / <1 / 1-3 / 3+ years."""

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        rows = []
        for text in X:
            years = years_required(text)
            words = [bool(re.search(p, text)) for p in LEVEL_WORDS.values()]
            buckets = [years is None] + ([False] * 3 if years is None else
                                         [years < 1, 1 <= years < 3, years >= 3])
            rows.append(words + buckets)
        return np.array(rows, dtype=float)


# --- smart baselines: simple rules, written as estimators so they fit in a Pipeline ----------

class KeywordLevelRule(BaseEstimator, ClassifierMixin):
    """A level word wins, else the years of experience, else the most frequent training level."""

    def fit(self, X, y):
        self.classes_, counts = np.unique(y, return_counts=True)
        self.fallback_ = self.classes_[np.argmax(counts)]
        return self

    def _one(self, text):
        years = years_required(text)
        return level_word(text) or (level_from_years(years) if years is not None else self.fallback_)

    def predict(self, X):
        return np.array([self._one(t) for t in X])


SALARY_KEYWORDS = [
    "data scien", "machine learning", "devops", "android", "ios", "flutter", "react native",
    "golang", "go developer", "java ", "kotlin", "python", "php", "laravel", ".net", "c#",
    "node", "react", "vue", "angular", "frontend", "front-end", "backend", "back-end",
    "fullstack", "full stack", "qa", "tester", "ui/ux", "designer", "1c", "analyst",
    "project manager", "product manager", "sysadmin", "системный администратор",
]


class KeywordSalaryMedian(BaseEstimator, RegressorMixin):
    """Smart baseline from the brief: median salary of posts with the same job-title keyword
    (e.g. "python"). Searched in the title lines (first 3 non-empty lines) first, then in the
    whole text; no keyword, or fewer than 5 posts with it -> the overall median."""

    @staticmethod
    def _keyword(text):
        title = " ".join([line for line in text.splitlines() if line.strip()][:3])
        for part in (title, text):
            found = next((k for k in SALARY_KEYWORDS if k in part), None)
            if found:
                return found
        return None

    def fit(self, X, y):
        y = np.asarray(y, dtype=float)
        keys = np.array([self._keyword(t) for t in X], dtype=object)
        self.overall_ = float(np.median(y))
        self.medians_ = {k: float(np.median(y[keys == k])) for k in set(keys) - {None}
                         if (keys == k).sum() >= 5}
        return self

    def predict(self, X):
        return np.array([self.medians_.get(self._keyword(t), self.overall_) for t in X])


# --- the candidates --------------------------------------------------------------------------

def tfidf():
    # words and word pairs, ignoring words in fewer than 3 posts.
    # token_pattern keeps 1-character tokens, so "3 years" keeps its "3".
    return TfidfVectorizer(ngram_range=(1, 2), min_df=3, max_features=20_000, sublinear_tf=True,
                           token_pattern=r"(?u)\b\w+\b")


def tfidf_and_hints():
    # the 7 hints get weight 3 so they are not drowned by thousands of word features
    return FeatureUnion([("tfidf", tfidf()), ("hints", LevelHints())],
                        transformer_weights={"tfidf": 1, "hints": 3})


def make(model, features=None):
    """clean -> [features] -> model, as one Pipeline."""
    steps = [("clean", FunctionTransformer(clean_texts))]
    if features is not None:
        steps.append(("features", features))
    return Pipeline(steps + [("model", model)])


def level_candidates():
    logreg = lambda: LogisticRegression(max_iter=3000, class_weight="balanced")
    return {
        "dummy_most_frequent": make(DummyClassifier(strategy="most_frequent")),
        "smart_keyword_rule": make(KeywordLevelRule()),
        "naive_bayes": make(MultinomialNB(alpha=0.5), tfidf()),
        "logistic_regression": make(logreg(), tfidf()),
        "naive_bayes_hints": make(MultinomialNB(alpha=0.5), tfidf_and_hints()),
        "logistic_regression_hints": make(logreg(), tfidf_and_hints()),
    }


def salary_candidates():
    knn = lambda: KNeighborsRegressor(n_neighbors=10, metric="cosine", weights="distance")
    return {
        "dummy_median": make(DummyRegressor(strategy="median")),
        "smart_keyword_median": make(KeywordSalaryMedian()),
        # Ridge = linear regression with a penalty, so thousands of word features don't overfit
        "linear_ridge": make(Ridge(alpha=1.0), tfidf()),
        "knn": make(knn(), tfidf()),
        "decision_tree": make(DecisionTreeRegressor(max_depth=8, min_samples_leaf=10,
                                                    random_state=0), tfidf()),
        "knn_hints": make(knn(), tfidf_and_hints()),
        # learns log(salary): salaries are skewed, so this overestimates less often
        "linear_ridge_hints_log": make(TransformedTargetRegressor(
            regressor=Ridge(alpha=1.0), func=np.log, inverse_func=np.exp), tfidf_and_hints()),
    }
