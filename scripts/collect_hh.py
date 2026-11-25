"""Collect IT vacancies from hh.uz (rules we follow: jobtracker/collect/hh_web.py).

Usage:
    python -m scripts.collect_hh                    # all active IT vacancies via hh's search (weekly)
    python -m scripts.collect_hh --probe            # parse 3 live pages, store nothing
    python -m scripts.collect_hh --limit 200        # small run
    python -m scripts.collect_hh --wayback 20260801 # past vacancies found in the Wayback Machine
Safe to stop with Ctrl+C and re-run: it resumes. Afterwards run `python -m scripts.extract`.
"""
import argparse
import itertools

from jobtracker.collect.hh_parse import parse_vacancy
from jobtracker.collect.hh_web import DELAY_SECONDS, SITE, Blocked, Client, collect_hh, search_ids, wayback_ids
from jobtracker.db import connect
from jobtracker.dedupe import assign_dup_groups


def probe(client, n=3):
    """Check the parser on a few live pages before a long run (page layouts change)."""
    for vid in itertools.islice(search_ids(client, roles=[96]), n):
        resp = client.get(f"{SITE}/vacancy/{vid}")
        print(f"\n--- {vid}: " + ("gone" if resp is None else repr(parse_vacancy(resp.text))[:600]))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe", action="store_true", help="parse 3 pages, store nothing")
    parser.add_argument("--limit", type=int, help="stop after this many vacancy pages")
    parser.add_argument("--wayback", metavar="YYYYMMDD", help="past vacancies captured since this date")
    parser.add_argument("--delay", type=float, default=DELAY_SECONDS, help="seconds between requests (min 3)")
    args = parser.parse_args(argv)

    client = Client(delay=max(DELAY_SECONDS, args.delay))
    if args.probe:
        return probe(client)

    conn = connect()
    try:
        ids = wayback_ids(args.wayback) if args.wayback else search_ids(client)
        print(f"done: {collect_hh(conn, ids, client, limit=args.limit)}")
    except Blocked as exc:
        print(f"STOPPED: {exc}. Wait a day before trying again; do not lower the delay.")
    except KeyboardInterrupt:
        print("stopped by hand; everything fetched so far is saved. Re-run to continue.")
    conn.commit()
    groups = assign_dup_groups(conn)          # hh posts are often reposted to Telegram channels too
    n_hh = conn.execute("SELECT COUNT(*) FROM raw_posts WHERE source = 'hh'").fetchone()[0]
    print(f"hh posts in DB: {n_hh}; unique vacancies overall (dup groups): {groups.nunique()}")


if __name__ == "__main__":
    main()
