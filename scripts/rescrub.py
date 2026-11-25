"""Re-apply the current PII rules to every stored post (run after improving clean.py),
then recompute duplicate groups. Prints how many rows changed and any obvious leftovers."""
from jobtracker.clean import scrub_pii, text_hash
from jobtracker.db import connect
from jobtracker.dedupe import assign_dup_groups

LEAK_SQL = """SELECT COUNT(*) FROM raw_posts WHERE text LIKE '%+998%' OR text LIKE '%https://%'
              OR text LIKE '%t.me/%' OR text LIKE '%@gmail%' OR text LIKE '%@mail.%'"""


def main():
    conn = connect()
    changed = 0
    for row in conn.execute("SELECT id, text FROM raw_posts").fetchall():
        clean = scrub_pii(row["text"])
        if clean != row["text"]:
            conn.execute("UPDATE raw_posts SET text = ?, text_hash = ? WHERE id = ?",
                         (clean, text_hash(clean), row["id"]))
            changed += 1
    conn.commit()
    groups = assign_dup_groups(conn)
    leaks = conn.execute(LEAK_SQL).fetchone()[0]
    print(f"rows changed: {changed}, unique vacancies: {groups.nunique()}, obvious leftovers: {leaks}")


if __name__ == "__main__":
    main()
