"""Collect posts from PUBLIC Telegram channels through the public web preview (t.me/s/<channel>).

No login is needed: these pages are what anyone sees in a browser. We go politely:
one request every ~1.5 s, an honest User-Agent, and we stop as soon as we reach posts we
already have (incremental), so weekly runs only fetch new messages.

Each page shows ~20 messages; '?before=<msg_id>' gives the previous page.
"""
import re
import time
from typing import Iterator, Optional

import requests
from bs4 import BeautifulSoup

from jobtracker.config import CHANNEL_KEEP
from jobtracker.db import insert_post

BASE = "https://t.me/s/{channel}"
HEADERS = {"User-Agent": "jobtracker-student-ml-project/0.1 (course project, polite crawler)"}
DELAY_SECONDS = 1.5
MIN_TEXT_CHARS = 40          # shorter posts are ads/announcements, not vacancies


def fetch_page(channel: str, before: Optional[int] = None) -> list:
    """The messages on one page as dicts: msg_id, posted_at, text (raw)."""
    resp = requests.get(BASE.format(channel=channel), params={"before": before} if before else None,
                        headers=HEADERS, timeout=20)
    resp.raise_for_status()
    messages = []
    for node in BeautifulSoup(resp.text, "html.parser").select("div.tgme_widget_message[data-post]"):
        text_node = node.select_one("div.tgme_widget_message_text")
        time_node = node.select_one("time[datetime]")
        if text_node is None or time_node is None:
            continue                                      # photo-only post, service message
        # <br> are the real line breaks; inline tags (<b>, <a>, emoji) must not split lines
        for br in text_node.find_all("br"):
            br.replace_with("\n")
        messages.append({"msg_id": int(node["data-post"].rsplit("/", 1)[1]),   # "uzdev_jobs/8447"
                         "posted_at": time_node["datetime"],
                         "text": text_node.get_text("").strip()})
    return messages


def iter_pages(channel: str, max_pages: int = 50) -> Iterator[list]:
    """Yield pages from newest to oldest."""
    before = None
    for _ in range(max_pages):
        page = fetch_page(channel, before)
        if not page:
            return
        yield page
        before = min(m["msg_id"] for m in page)
        if before <= 1:
            return
        time.sleep(DELAY_SECONDS)


def collect_channel(conn, channel: str, max_pages: int = 50, full: bool = False) -> int:
    """Store new posts from one channel; returns how many were new.

    Incremental by default: stops at the first page whose kept posts are all stored already.
    full=True keeps going back to max_pages (first backfill)."""
    keep = re.compile(CHANNEL_KEEP.get(channel, ""), re.IGNORECASE)
    inserted = 0
    for page in iter_pages(channel, max_pages):
        # skip short posts, and posts the channel rule rejects (e.g. job seekers' personal data)
        kept = [m for m in page if len(m["text"]) >= MIN_TEXT_CHARS and keep.search(m["text"])]
        new = sum(insert_post(conn, "telegram", channel, m["msg_id"], m["posted_at"], m["text"])
                  for m in kept)
        conn.commit()
        inserted += new
        # a page where everything was filtered out says nothing about old data: keep paging
        if kept and not new and not full:
            break
    return inserted
