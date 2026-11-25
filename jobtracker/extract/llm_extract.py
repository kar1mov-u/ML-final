"""Run the LLM extraction (Google Gemini, free tier) and store results in the `vacancies` table.

How it works
- Several posts go in ONE request (default 10): the free tier limits requests per day, not posts.
- Gemini returns a JSON list (structured output); each item carries the post id we sent, so
  answers are matched to posts by id, never by position. Every item is validated with Pydantic;
  bad items are skipped and retried on the next run.
- Only one post per duplicate group is extracted, and never twice (posts already in `vacancies`
  are skipped), so the script can be stopped and re-run any time.
- Rate limits: a pause between requests (rpm) and back-off on HTTP 429. When the daily quota is
  used up we stop cleanly; the next run continues where this one stopped.

Privacy: free-tier requests may be used by Google. We only send posts that were already scrubbed
of phone numbers, e-mails, @usernames, links and names.
"""
import json
import time
from datetime import datetime
from typing import Optional

import httpx2 as httpx   # the HTTP library google-genai uses
from google import genai
from google.genai import errors, types
from pydantic import ValidationError

from jobtracker.config import EXTRACT_MODEL, FALLBACK_MODEL, PROMPT_VERSION
from jobtracker.db import utc_now
from jobtracker.extract.schema import SYSTEM_PROMPT, Extraction, PostExtraction
from jobtracker.salary import to_usd_month

POSTS_PER_REQUEST = 10
MAX_RETRIES = 4           # per request, on 429 / 5xx
TIMEOUT_MS = 120_000      # give up on a request after 2 minutes (e.g. after the laptop slept)
CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    response_mime_type="application/json",
    response_schema=list[PostExtraction],   # the SDK turns the Pydantic model into a JSON schema
    temperature=0,                           # same post -> same labels
)


class QuotaExhausted(Exception):
    """Still rate-limited after all retries: most likely the daily free quota is used up."""


class ServerBusy(Exception):
    """Gemini kept failing (overloaded / network); these posts are retried on the next run."""


def pending_posts(conn, limit: Optional[int] = None):
    """Group leaders that have not been extracted yet, oldest first."""
    sql = """SELECT r.id, r.text FROM raw_posts r
             LEFT JOIN vacancies v ON v.raw_id = r.id
             WHERE v.raw_id IS NULL AND (r.dup_group IS NULL OR r.dup_group = r.id)
             ORDER BY r.posted_at"""
    return conn.execute(sql + (f" LIMIT {int(limit)}" if limit else "")).fetchall()


def final_level(ex: Extraction) -> str:
    """The level label rule, applied in code so it is the same for every post:
    1. a level named in the post (found by the LLM) wins;
    2. otherwise the required years: <1 junior, 1 to <3 middle, 3+ senior;
    3. otherwise unknown (left out of level training)."""
    if ex.level_evidence == "title" and ex.level != "unknown":
        return ex.level
    years = ex.years_experience_min
    if years is None:
        return "unknown"
    return "junior" if years < 1 else "middle" if years < 3 else "senior"


def save(conn, ex: PostExtraction, model: str) -> None:
    conn.execute(
        """INSERT OR REPLACE INTO vacancies
           (raw_id, is_job_post, is_it_job, title, level, salary_min, salary_max, currency,
            salary_period, salary_usd, skills, language, extracted_json, llm_model,
            prompt_version, extracted_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (ex.post_id, int(ex.is_job_post), int(ex.is_it_job), ex.title, final_level(ex),
         ex.salary_min, ex.salary_max, ex.currency, ex.salary_period,
         to_usd_month(ex.salary_min, ex.salary_max, ex.currency, ex.salary_period),
         json.dumps(ex.skills), ex.language, ex.model_dump_json(exclude={"post_id"}),
         model, PROMPT_VERSION, utc_now()),
    )


def _call(client, model: str, rows, retries: int = MAX_RETRIES) -> list:
    """One request with retries (longer waits each time). Returns the valid answers."""
    posts = "\n\n".join(f'<post id="{r["id"]}">\n{r["text"]}\n</post>' for r in rows)
    prompt = (f"Extract the fields for each of the {len(rows)} posts below. "
              f"Return one item per post, with post_id equal to the post's id.\n\n{posts}")
    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt, config=CONFIG)
            return _parse(response.text, {r["id"] for r in rows})
        except httpx.TransportError as exc:          # timeout / lost connection
            if attempt == retries:
                raise ServerBusy(str(exc)) from exc
            wait, why = 30, type(exc).__name__
        except errors.APIError as exc:
            if exc.code != 429 and (exc.code or 0) < 500:
                raise
            if attempt == retries:
                raise (QuotaExhausted if exc.code == 429 else ServerBusy)(str(exc)) from exc
            wait, why = 30 * (attempt + 1), f"HTTP {exc.code}"
        print(f"  {model}: {why}, waiting {wait}s (attempt {attempt + 1}/{retries})")
        time.sleep(wait)


def _parse(text: Optional[str], wanted_ids: set) -> list:
    """Valid items that answer a post we actually sent."""
    try:
        items = json.loads(text or "[]")
    except json.JSONDecodeError:
        return []
    found = {}
    for item in items if isinstance(items, list) else []:
        try:
            ex = PostExtraction.model_validate(item)
        except ValidationError:
            continue
        if ex.post_id in wanted_ids:
            found[ex.post_id] = ex
    return list(found.values())


def _ask(client, model: str, rows):
    """(answers, model used). If the main model stays overloaded, the fallback model answers
    (every row stores which model labelled it, so this stays traceable)."""
    try:
        return _call(client, model, rows, retries=1), model
    except ServerBusy:
        if not FALLBACK_MODEL or FALLBACK_MODEL == model:
            raise
        print(f"  {model} overloaded, using {FALLBACK_MODEL}")
        return _call(client, FALLBACK_MODEL, rows), FALLBACK_MODEL


def extract(conn, limit: Optional[int] = None, model: str = EXTRACT_MODEL,
            per_request: int = POSTS_PER_REQUEST, rpm: int = 10) -> dict:
    """Extract all pending posts. Commits after every request, so progress is never lost."""
    client = genai.Client(http_options=types.HttpOptions(timeout=TIMEOUT_MS))  # GEMINI_API_KEY
    rows = pending_posts(conn, limit)
    chunks = [rows[i:i + per_request] for i in range(0, len(rows), per_request)]
    stats = {"ok": 0, "failed": 0, "requests": 0}
    busy_in_a_row = 0

    for n, chunk in enumerate(chunks, 1):
        started = time.monotonic()
        try:
            found, used = _ask(client, model, chunk)
        except QuotaExhausted:
            print("Rate limit still hit after retries (daily free quota used up?). "
                  "Progress is saved: run the same command again later.")
            break
        except ServerBusy:
            stats["failed"] += len(chunk)
            busy_in_a_row += 1
            print(f"request {n}/{len(chunks)}: Gemini overloaded, skipped (retried on the next run)")
            if busy_in_a_row >= 5:
                print("Gemini overloaded 5 requests in a row: stopping. Run the same command later.")
                break
            continue
        busy_in_a_row = 0
        for ex in found:
            save(conn, ex, used)
        conn.commit()
        stats["requests"] += 1
        stats["ok"] += len(found)
        stats["failed"] += len(chunk) - len(found)
        print(f"{datetime.now():%H:%M:%S} request {n}/{len(chunks)}: {len(found)}/{len(chunk)} posts ok ({used})")
        time.sleep(max(0.0, 60 / rpm - (time.monotonic() - started)))
    return stats
