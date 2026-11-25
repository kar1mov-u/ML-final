"""Collect new posts from all configured Telegram channels, then refresh duplicate groups.

Usage:
    python -m scripts.collect                      # weekly incremental run
    python -m scripts.collect --full --pages 200   # first backfill (older history)
"""
import argparse

from jobtracker.collect.telegram_web import collect_channel
from jobtracker.config import CHANNELS
from jobtracker.db import connect
from jobtracker.dedupe import assign_dup_groups


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="keep paging back even past known posts")
    parser.add_argument("--pages", type=int, default=50, help="max pages per channel (~20 posts each)")
    parser.add_argument("--channels", nargs="*", default=CHANNELS)
    args = parser.parse_args(argv)

    conn = connect()
    for channel in args.channels:
        try:
            print(f"{channel:25s} +{collect_channel(conn, channel, args.pages, args.full)} new posts")
        except Exception as exc:                    # one broken channel must not stop the run
            print(f"{channel:25s} FAILED: {exc}")

    groups = assign_dup_groups(conn)
    total = conn.execute("SELECT COUNT(*) FROM raw_posts").fetchone()[0]
    print(f"total posts: {total}, unique vacancies (dup groups): {groups.nunique()}")


if __name__ == "__main__":
    main()
