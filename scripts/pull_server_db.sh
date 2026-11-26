#!/usr/bin/env bash
# Download a copy of the LIVE database from Railway to data/server.db (open it in DataGrip).
#
#   bash scripts/pull_server_db.sh
#
# Needs: `railway login` and an SSH key registered with Railway (`railway ssh keys add`).
# It is a snapshot: it does not change when the server changes. Run again for a fresh copy.
# Your local data/jobs.db is not touched.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "1/3 making a consistent snapshot on the server (safe while the app is running)"
railway ssh --service web -- python -c "
import gzip, shutil, sqlite3
src = sqlite3.connect('/app/data/jobs.db'); dst = sqlite3.connect('/app/data/snapshot.db')
src.backup(dst); dst.close()
with open('/app/data/snapshot.db', 'rb') as f, gzip.open('/app/data/snapshot.db.gz', 'wb') as g:
    shutil.copyfileobj(f, g)
" < /dev/null

echo "2/3 downloading (about 6 MB, can take a minute or two)"
rm -f data/server.db.gz
railway volume files --volume web-volume download snapshot.db.gz data/server.db.gz < /dev/null
gunzip -f data/server.db.gz

echo "3/3 checking"
sqlite3 data/server.db "pragma integrity_check;"
sqlite3 data/server.db "select 'posts: ' || count(*) from raw_posts; select 'predictions: ' || count(*) from prediction_log;"
echo "Done: data/server.db"
