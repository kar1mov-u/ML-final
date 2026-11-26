#!/usr/bin/env bash
# Deploy the newest code / model from GitHub to the server:  sudo bash /srv/jobtracker/deploy/update.sh
set -euo pipefail
cd /srv/jobtracker
sudo -u jobtracker git pull --ff-only
sudo -u jobtracker .venv/bin/pip install -q -r requirements.txt
systemctl restart jobtracker
sleep 3 && curl -s localhost:8000/health && echo
