"""The weekly job (cron, every Monday 06:00 on the server; see deploy/crontab.txt).

    python -m scripts.weekly

1. collect: new Telegram posts + new hh.uz IT vacancies (personal data removed, dedupe refreshed)
2. extract: Gemini labels the new unique posts (resumable, never pays twice)
3. retrain: only after the v1 release (before it, the newest weeks are the frozen test set).
            The promotion gate decides; the app picks up a changed models/LIVE by itself.
"""
from datetime import datetime

import retrain
from jobtracker.db import connect
from jobtracker.extract.llm_extract import extract
from jobtracker.registry import released
from scripts import collect, collect_hh


def main():
    print(f"=== weekly run {datetime.now():%Y-%m-%d %H:%M} ===")
    collect.main([])
    collect_hh.main([])                              # stops by itself if hh blocks us
    print(extract(connect()))
    if not released():
        print("retrain: skipped (v1 not released yet; newest weeks are the frozen test set)")
        return
    try:
        retrain.main([])
    except SystemExit as exc:                        # retrain.py exits with a message when it can't run
        print(f"retrain: not run ({exc})")


if __name__ == "__main__":
    main()
