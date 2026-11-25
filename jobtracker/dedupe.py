"""Duplicate detection. The same vacancy is often reposted (same channel weeks later,
or another channel). Copies must stay on the same side of the train/test split, and we
must not pay the LLM twice for them.

Every post gets dup_group = id of the first (oldest) post of its group:
1. exact duplicates   -> same normalised-text hash
2. near duplicates    -> TF-IDF cosine similarity >= THRESHOLD with an earlier post
"""
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from jobtracker.clean import normalize

THRESHOLD = 0.90


def assign_dup_groups(conn, threshold: float = THRESHOLD) -> pd.Series:
    """Recompute dup_group for all posts (cheap at our scale: a few thousand rows)."""
    df = pd.read_sql("SELECT id, text, text_hash, posted_at FROM raw_posts ORDER BY posted_at, id", conn)
    if df.empty:
        return pd.Series(dtype=int)

    group = {}
    # 1. exact: the earliest post with the same hash is the group leader
    first_by_hash = df.groupby("text_hash")["id"].transform("first")
    df["group"] = first_by_hash

    # 2. near duplicates among the remaining leaders
    leaders = df[df["id"] == df["group"]].reset_index(drop=True)
    if len(leaders) > 1:
        tfidf = TfidfVectorizer(preprocessor=normalize, ngram_range=(1, 2), min_df=1)
        X = tfidf.fit_transform(leaders["text"])
        sim = cosine_similarity(X, dense_output=False)
        leader_of = {}
        for i in range(len(leaders)):
            row = sim.getrow(i)
            # earlier leaders (lower index = earlier, rows are sorted by time) that are similar
            earlier = [j for j, s in zip(row.indices, row.data) if j < i and s >= threshold]
            if earlier:
                root = leader_of.get(min(earlier), leaders.at[min(earlier), "id"])
                leader_of[i] = root
        for i, root in leader_of.items():
            group[leaders.at[i, "id"]] = root
        df["group"] = df["group"].map(lambda g: group.get(g, g))

    conn.executemany("UPDATE raw_posts SET dup_group = ? WHERE id = ?",
                     list(zip(df["group"].astype(int), df["id"].astype(int))))
    conn.commit()
    return df.set_index("id")["group"]
