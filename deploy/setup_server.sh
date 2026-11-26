#!/usr/bin/env bash
# One-time setup of a fresh Google Cloud e2-micro VM (Ubuntu 24.04). Safe to run again.
#
#   curl -fsSL https://raw.githubusercontent.com/kar1mov-u/ML-final/main/deploy/setup_server.sh | sudo bash
#
# What it does:
#   1. installs Python, git, sqlite3 and Caddy (HTTPS), adds 1 GB swap (the VM has 1 GB RAM)
#   2. clones the repo to /srv/jobtracker and installs the Python packages
#   3. starts the app with systemd (restarts after a crash and on every boot)
#   4. gives it an HTTPS address: <your-ip>.sslip.io (free, no domain needed)
#   5. installs the cron jobs (weekly collect + extract, nightly DB backup)
# Afterwards: put GEMINI_API_KEY in /srv/jobtracker/.env and upload data/jobs.db (see README).
set -euo pipefail

REPO=https://github.com/kar1mov-u/ML-final.git
APP=/srv/jobtracker

echo "== 1. system packages, swap, time zone"
apt-get update -q
apt-get install -y -q python3-venv python3-pip git sqlite3 caddy
if ! swapon --show | grep -q /swapfile; then
    fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
    echo "/swapfile none swap sw 0 0" >> /etc/fstab
fi
timedatectl set-timezone Asia/Tashkent          # cron times below are Tashkent time

echo "== 2. code and Python packages"
id jobtracker >/dev/null 2>&1 || adduser --system --group --home "$APP" jobtracker
if [ ! -d "$APP/.git" ]; then
    git clone "$REPO" /tmp/jobtracker-clone
    cp -a /tmp/jobtracker-clone/. "$APP"/ && rm -rf /tmp/jobtracker-clone
fi
mkdir -p "$APP/data"
[ -f "$APP/.env" ] || cp "$APP/.env.example" "$APP/.env"
chmod 600 "$APP/.env"
chown -R jobtracker:jobtracker "$APP"
sudo -u jobtracker python3 -m venv "$APP/.venv"
sudo -u jobtracker "$APP/.venv/bin/pip" install -q --upgrade pip
sudo -u jobtracker "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

echo "== 3. app service (systemd)"
cp "$APP/deploy/jobtracker.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable jobtracker
systemctl restart jobtracker || true             # fails until jobs.db + a model exist; fine

echo "== 4. HTTPS with Caddy"
IP=$(curl -s -H "Metadata-Flavor: Google" \
     http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip)
DOMAIN="${IP//./-}.sslip.io"                     # 34.1.2.3 -> 34-1-2-3.sslip.io
cat > /etc/caddy/Caddyfile <<EOF
$DOMAIN {
    reverse_proxy 127.0.0.1:8000
}
EOF
systemctl reload caddy || systemctl restart caddy

echo "== 5. cron jobs"
crontab -u jobtracker "$APP/deploy/crontab.txt"

echo
echo "Done. Your address: https://$DOMAIN"
echo "Next: 1) sudo nano $APP/.env   (GEMINI_API_KEY=...)"
echo "      2) upload jobs.db to $APP/data/ and run: sudo chown jobtracker:jobtracker $APP/data/jobs.db"
echo "      3) sudo systemctl restart jobtracker && curl -s localhost:8000/health"
