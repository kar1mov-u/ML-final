"""Runs the weekly job inside the web app (used on Railway, where a separate cron service cannot
reach the app's volume). Turned on with WEEKLY_JOB=on; off by default (laptop, VM with cron).

Every 30 minutes a background thread checks: is it Monday after 06:00 Tashkent time, and has the
job not run this week yet? Then it runs scripts/weekly.py once and remembers the week in a file
on the volume, so a restart does not run it twice.
"""
import os
import threading
import time
import traceback

from jobtracker.config import DB_PATH, TASHKENT

MARKER = DB_PATH.parent / "weekly_last_run.txt"      # e.g. "2026-W48"


def due(now, last_run):
    week = now.strftime("%G-W%V")
    return now.weekday() == 0 and now.hour >= 6 and last_run != week, week


def _loop():
    from datetime import datetime
    from scripts import weekly                     # imported here: heavy, only needed when it runs
    while True:
        last = MARKER.read_text().strip() if MARKER.exists() else ""
        run_now, week = due(datetime.now(TASHKENT), last)
        if run_now:
            try:
                weekly.main()
            except Exception:                      # the web app must keep running whatever happens
                traceback.print_exc()
            MARKER.write_text(week)
        time.sleep(30 * 60)


def start():
    if os.getenv("WEEKLY_JOB") == "on":
        threading.Thread(target=_loop, daemon=True, name="weekly-job").start()
