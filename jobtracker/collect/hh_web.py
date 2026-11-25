"""Collect IT vacancies from hh.uz (instructor-approved source; hh's written permission for the
search pages: docs/hh_permission.md).

Where the vacancy ids come from
- search_ids():  hh's vacancy search for the 21 IT professional roles in Uzbekistan. This is the
                 ONLY query-string URL we request (robots.txt disallows '*?*' for crawlers in
                 general; hh allowed it for this project). For logged-out visitors hh shows only
                 ACTIVE vacancies (archived=true and date filters are ignored, tested 2026-11-22).
- wayback_ids(): past vacancy ids from the Internet Archive's public index. Archived vacancies
                 stay viewable at /vacancy/<id>.

How we fetch (Client)
- one request at a time, a delay between requests, honest User-Agent, robots.txt checked
- 403 / 429 / captcha / repeated slow answers -> Blocked: the run stops, we never work around it
  (a 403 "restricted vacancy" page is not a block: it is skipped like a 404)
- incremental: ids already stored (raw_posts) or rejected as non-IT (hh_skipped) are skipped

What we store
- raw_posts (via db.insert_post, which removes personal data): source='hh', msg_id=<vacancy id>
- hh_meta: hh's structured fields (salary, experience, skills), used to check the LLM's labels
"""
import json
import re
import time
from typing import Iterable, Iterator, Optional
from urllib import robotparser

import requests

from jobtracker.collect.hh_parse import Vacancy, parse_vacancy, to_utc
from jobtracker.db import insert_post, utc_now

SITE = "https://hh.uz"
USER_AGENT = "jobtracker-student-ml-project/0.1 (university course project, polite crawler)"
HEADERS = {"User-Agent": USER_AGENT, "Accept-Language": "ru,uz;q=0.8,en;q=0.5"}
DELAY_SECONDS = 3.0
RESTRICTED_MARK = "недоступна эта вакансия"   # text of hh's "restricted vacancy" page (HTTP 403)
SLOW_SECONDS = 10                             # 3 answers slower than this in a row = soft block
SOURCE, CHANNEL = "hh", "hh.uz"

SEARCH_URL = f"{SITE}/search/vacancy?"
AREA_UZBEKISTAN = 97
# hh professional roles in "Информационные технологии" (api.hh.ru/professional_roles),
# without the design/art roles (12, 25, 34) and methodologist (155).
IT_ROLES = [96, 104, 124, 160, 113, 114, 112, 116, 121, 10, 148, 150, 156, 157, 164, 165,
            73, 107, 125, 36, 126]
MAX_PAGES_PER_ROLE = 40                       # hh never shows more than ~2,000 results


class Blocked(RuntimeError):
    """hh.uz is blocking or slowing us down. The run stops; we never work around it."""


class Client:
    """requests.Session + robots.txt check + delay + stop on blocks."""

    def __init__(self, delay: float = DELAY_SECONDS):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay
        self._last = 0.0
        self._slow = 0
        self._robots = {}

    def get(self, url: str) -> Optional[requests.Response]:
        """The response, or None when the vacancy is gone (404/410) or restricted."""
        if not self._allowed(url):
            raise PermissionError(f"robots.txt does not allow {url}")
        return self._request(url)

    def _allowed(self, url: str) -> bool:
        if url.startswith(SEARCH_URL):       # allowed by hh in writing (see module docstring)
            return True
        if "?" in url:                       # hh.uz robots.txt: 'Disallow: *?*'
            return False
        host = re.match(r"https?://[^/]+", url).group(0)
        if host not in self._robots:
            resp = self._request(f"{host}/robots.txt")
            if resp is None:
                raise RuntimeError(f"{host}/robots.txt not found; not crawling")
            self._robots[host] = robotparser.RobotFileParser()
            self._robots[host].parse(resp.text.splitlines())
        return self._robots[host].can_fetch(USER_AGENT, url)

    def _fetch(self, url: str) -> requests.Response:
        """One GET; a network hiccup is retried once after a minute, a second one stops the run."""
        try:
            return self.session.get(url, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            print(f"  network hiccup at {url} ({type(exc).__name__}); retrying in 60 s", flush=True)
        time.sleep(60)
        try:
            return self.session.get(url, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as exc:
            raise Blocked(f"hh.uz is not answering ({type(exc).__name__} twice at {url})")

    def _request(self, url: str) -> Optional[requests.Response]:
        time.sleep(max(0.0, self.delay - (time.monotonic() - self._last)))
        started = time.monotonic()
        resp = self._fetch(url)
        self._last = time.monotonic()
        self._slow = self._slow + 1 if self._last - started > SLOW_SECONDS else 0
        if self._slow >= 3:
            raise Blocked(f"hh.uz answers slowly ({SLOW_SECONDS}+ s, 3 times in a row)")

        if resp.status_code in (404, 410):
            return None
        # some vacancies are visible only to logged-in users: hh answers 403 with this text
        if resp.status_code == 403 and RESTRICTED_MARK in resp.text:
            return None
        if resp.status_code in (403, 429) or "captcha" in resp.url.lower():
            raise Blocked(f"hh.uz blocked us ({resp.status_code} at {resp.url})")
        resp.raise_for_status()
        return resp


# --- where the ids come from -----------------------------------------------------------------

def _vacancy_ids(text: str) -> set:
    return set(map(int, re.findall(r"/vacancy/(\d+)", text)))


def search_url(role: int, page: int) -> str:
    return (f"{SEARCH_URL}area={AREA_UZBEKISTAN}&professional_role={role}"
            f"&items_on_page=100&page={page}")


def search_ids(client: Client, roles=IT_ROLES, log=print) -> Iterator[int]:
    """Every vacancy id hh's search shows for our IT roles; paging stops when no new ids come."""
    seen = set()
    for i, role in enumerate(roles, 1):
        for page in range(MAX_PAGES_PER_ROLE):
            resp = client.get(search_url(role, page))
            new = (_vacancy_ids(resp.text) if resp is not None else set()) - seen
            if not new:
                break
            seen |= new
            yield from sorted(new)
        log(f"  search: role {role} done ({i}/{len(roles)}), {len(seen)} ids so far")


def wayback_ids(since: str = "20260801", log=print) -> list:
    """hh.uz vacancy ids the Wayback Machine captured since `since` (YYYYMMDD), newest first."""
    found = set()
    for host in ("hh.uz", "tashkent.hh.uz"):
        url = (f"https://web.archive.org/cdx/search/cdx?url={host}/vacancy/*&from={since}"
               f"&collapse=urlkey&fl=original&limit=50000")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=240)
            resp.raise_for_status()
            found |= _vacancy_ids(resp.text)
        except requests.RequestException as exc:
            log(f"  wayback index for {host} failed ({type(exc).__name__}); try again later")
    return sorted(found, reverse=True)


# --- the collection run ----------------------------------------------------------------------

def known_ids(conn) -> set:
    stored = conn.execute("SELECT msg_id FROM raw_posts WHERE source = ?", (SOURCE,))
    skipped = conn.execute("SELECT vacancy_id FROM hh_skipped")
    return {r[0] for r in stored} | {r[0] for r in skipped}


def store(conn, vid: int, v: Vacancy) -> str:
    """Save one parsed vacancy. Returns what happened: stored / duplicate / not_it."""
    if not v.looks_it():
        conn.execute("INSERT OR IGNORE INTO hh_skipped (vacancy_id, title, checked_at) VALUES (?, ?, ?)",
                     (vid, v.title[:200], utc_now()))
        return "not_it"
    new = insert_post(conn, SOURCE, CHANNEL, vid, to_utc(v.posted_at) or utc_now(), v.post_text())
    s = v.salary
    conn.execute(
        """INSERT OR REPLACE INTO hh_meta (vacancy_id, salary_from, salary_to, currency,
           salary_period, gross, salary_text, experience, skills, collected_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (vid, s["from"], s["to"], s["currency"], s["period"],
         None if s["gross"] is None else int(s["gross"]), s["text"], v.experience,
         json.dumps(v.skills, ensure_ascii=False), utc_now()),
    )
    return "stored" if new else "duplicate"


def collect_hh(conn, ids: Iterable[int], client: Optional[Client] = None,
               limit: Optional[int] = None, log=print) -> dict:
    """Fetch the vacancy pages of the new ids (newest first) and store the IT ones.
    Commits every 25 pages, so it is safe to stop and re-run. Blocked propagates: stop the run."""
    client = client or Client()
    seen = known_ids(conn)
    todo = sorted({vid for vid in ids if vid not in seen}, reverse=True)[:limit]
    log(f"hh.uz: {len(seen)} ids already known, {len(todo)} new vacancy pages to check")

    stats = {"stored": 0, "duplicate": 0, "not_it": 0, "gone": 0, "no_text": 0}
    for i, vid in enumerate(todo, 1):
        resp = client.get(f"{SITE}/vacancy/{vid}")
        v = parse_vacancy(resp.text) if resp is not None else None
        if v is None:
            stats["gone"] += 1
        elif not v.title or len(v.description) < 40:
            stats["no_text"] += 1                        # page layout changed? run --probe
        else:
            stats[store(conn, vid, v)] += 1
        if i % 25 == 0:
            conn.commit()
            log(f"  {i}/{len(todo)}  {stats}")
    conn.commit()
    return stats
