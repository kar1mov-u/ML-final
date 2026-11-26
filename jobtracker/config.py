"""Project-wide settings. Secrets come from environment variables (.env), never from code."""
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DB_PATH = Path(os.getenv("DB_PATH", ROOT / "data" / "jobs.db"))
# Models shipped in git live in models/. On Railway the models live on the volume instead
# (MODELS_DIR=/app/data/models), so a model promoted by the weekly retrain survives redeploys;
# registry.sync_from_repo() copies the git models over at start-up.
REPO_MODELS_DIR = ROOT / "models"
MODELS_DIR = Path(os.getenv("MODELS_DIR", REPO_MODELS_DIR))

# The handbook asks for Tashkent time in the prediction log.
TASHKENT = ZoneInfo("Asia/Tashkent")

# Public Telegram IT job channels we collect from (public web preview t.me/s/<name>).
# Add/remove channels here; every collected post records its channel.
CHANNELS = [
    "uzdev_jobs",        # IT vacancies, ru/uz, often with $ salary
    "uzpythonjobs",      # Python vacancies (low volume)
    "click_jobs",        # Clickjobs aggregator; mixes IT and non-IT (is_it_job filters later)
    "UstozShogird",      # high volume; employer posts only (see CHANNEL_KEEP)
    "it_jobs_uz",
    "itvakansiyalar",
]

# Optional per-channel rule: keep only posts whose text matches this regex.
# UstozShogird also publishes job-SEEKER posts ("Ish joyi kerak") with a person's name,
# age and phone: those are personal data and not vacancies, so we never store them.
CHANNEL_KEEP = {
    "UstozShogird": r"^\W*Xodim kerak",
}

# LLM extraction (data cleaning only).
# Google Gemini free tier (key from https://aistudio.google.com/apikey in .env as GEMINI_API_KEY).
EXTRACT_MODEL = os.getenv("EXTRACT_MODEL", "gemini-3.5-flash-lite")
# Used for a request when the main model answers "overloaded" (HTTP 503) twice. Empty = off.
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "gemini-3.1-flash-lite")
PROMPT_VERSION = "v2"   # v2: "no experience" -> years 0; level rule applied in code

# --- Train / test split (fixed on day one, 2026-11-18; never move it) -----------------------
# Posts published on or after this date form the TEST set. It is used once, at release (v1).
# Model choice uses time-ordered cross-validation on the older posts only.
TEST_START = "2026-09-01"

# --- Serving --------------------------------------------------------------------------------
# Which model the app loads: this env var if set, else the version in models/LIVE, else the newest
# models/model_vN.joblib. Roll back: write the old version into models/LIVE and restart the app.
MODEL_VERSION = os.getenv("MODEL_VERSION", "")
