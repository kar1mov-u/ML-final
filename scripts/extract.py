"""Extract structured fields from collected posts with Gemini (needs GEMINI_API_KEY in .env).

Usage:
    python -m scripts.extract --limit 20      # small test first, then check the rows
    python -m scripts.extract                 # everything pending (stops cleanly at the daily quota)
    python -m scripts.extract --dry-run       # only count pending posts
"""
import argparse

from jobtracker.config import EXTRACT_MODEL
from jobtracker.db import connect
from jobtracker.extract.llm_extract import POSTS_PER_REQUEST, extract, pending_posts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=EXTRACT_MODEL)
    parser.add_argument("--per-request", type=int, default=POSTS_PER_REQUEST,
                        help="posts packed into one API request")
    parser.add_argument("--rpm", type=int, default=10, help="max requests per minute")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = connect()
    pending = len(pending_posts(conn, args.limit))
    requests = -(-pending // args.per_request)
    print(f"{pending} posts to extract with {args.model} (~{requests} requests)")
    if args.dry_run or pending == 0:
        return
    print(extract(conn, args.limit, args.model, args.per_request, args.rpm))


if __name__ == "__main__":
    main()
