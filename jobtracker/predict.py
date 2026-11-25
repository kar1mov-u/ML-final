"""Everything the app needs to answer one request: input checks, the model, the prediction log.

No LLM here: the saved scikit-learn pipelines read the raw text directly.
"""
import json
import re

from jobtracker.clean import scrub_pii
from jobtracker.data import LEVELS
from jobtracker.db import tashkent_now
from jobtracker.registry import live_version, load
from jobtracker.salary import MAX_USD, MIN_USD

MIN_WORDS = 8
MAX_CHARS = 6000
LOGGED_CHARS = 500         # the log keeps only the start of the input

# Words that show the text is about an IT job. Used only for a friendly warning.
IT_HINTS = re.compile(
    r"develop|разработ|dasturch|programm|программ|engineer|инженер|python|java|php|react|"
    r"frontend|backend|devops|\bqa\b|test|data|sql|android|ios|designer|дизайн|analyst|аналит|"
    r"1c|admin|админ|\bit\b|software|web|mobile",
    re.IGNORECASE,
)


def check_input(text):
    """Return (error, warning). error = cannot predict; warning = predict but tell the user."""
    if not isinstance(text, str):
        return "Please send the vacancy as text.", None
    text = text.strip()
    if not text:
        return "The text is empty. Paste a job vacancy.", None
    if len(text) > MAX_CHARS:
        return f"The text is too long (max {MAX_CHARS} characters). Paste one vacancy.", None
    if len(re.findall(r"\w+", text)) < MIN_WORDS:
        return (f"The text is too short (at least {MIN_WORDS} words). Paste the full vacancy "
                "with role, requirements and experience.", None)
    if not IT_HINTS.search(text):
        return None, ("This does not look like an IT vacancy. The model was trained on IT jobs, "
                      "so the estimate may be far off.")
    return None, None


class Predictor:
    """One model version, loaded once."""

    def __init__(self, version=None):
        self.version = version or live_version()
        models, self.meta = load(self.version)
        self.level_model, self.salary_model = models["level"], models["salary"]

    def predict(self, text):
        confidence = None                                    # rule baselines have none
        if hasattr(self.level_model, "predict_proba"):
            confidence = round(float(self.level_model.predict_proba([text])[0].max()), 2)
        salary = float(self.salary_model.predict([text])[0])
        margin = self.meta["salary_cv_mae"]                  # typical error from CV
        return {
            "level": str(self.level_model.predict([text])[0]),
            "confidence": confidence,
            "salary_usd": round(salary, -1),
            "salary_low": max(MIN_USD, round(salary - margin, -1)),
            "salary_high": round(salary + margin, -1),
            "model_version": self.version,
        }


def log_prediction(conn, text, result):
    """One row per request, input without personal data. Returns the row id (for feedback)."""
    prediction = {k: result[k] for k in ("level", "salary_usd", "salary_low", "salary_high")}
    cur = conn.execute(
        "INSERT INTO prediction_log (time, input, prediction, confidence, model_version)"
        " VALUES (?, ?, ?, ?, ?)",
        (tashkent_now(), scrub_pii(text)[:LOGGED_CHARS], json.dumps(prediction),
         result["confidence"], result["model_version"]),
    )
    conn.commit()
    return cur.lastrowid


def check_feedback(level, salary):
    """Validate a user's correction. Returns (error, label dict)."""
    label = {}
    if level:
        if level not in LEVELS:
            return "Level must be junior, middle or senior.", None
        label["level"] = level
    if salary not in (None, ""):
        try:
            salary = float(salary)
        except (TypeError, ValueError):
            return "Salary must be a number (USD per month).", None
        if not MIN_USD <= salary <= MAX_USD:
            return f"Salary must be between {MIN_USD} and {MAX_USD:,} USD per month.", None
        label["salary_usd"] = salary
    if not label:
        return "Choose a level or enter a salary.", None
    return None, label


def save_feedback(conn, prediction_id, label):
    """Store a user's correction as the label of that prediction (feedback loop)."""
    updated = conn.execute("UPDATE prediction_log SET label = ?, label_time = ? WHERE id = ?",
                           (json.dumps(label), tashkent_now(), prediction_id)).rowcount
    conn.commit()
    return updated == 1
