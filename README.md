# Uzbekistan IT Job Market Tracker
Estimates the level (junior / middle / senior) and monthly salary of an IT job posting in Uzbekistan,
and shows a weekly view of the skills employers ask for. Built for students and the career centre.

Live link: _TBD_

## Result
Cross-validation on the training part (5 time-ordered folds; test set untouched until v1):

| Model | Level macro F1 | Salary MAE (USD) |
|---|---|---|
| Dummy (most frequent / median) | 0.24 | 712 |
| Smart baseline (keyword rule / title-keyword median) | **0.75** | 699 |
| Naive Bayes / Logistic regression | 0.35 / 0.56 | – |
| Linear (Ridge) / kNN / Decision tree | – | 571 / 620 / 660 |
| LogReg + level hints | **0.825** | – |
| Ridge + level hints, log(salary) | – | **524** |

Best so far (CV): **logistic regression + level hints, macro F1 0.825** and **Ridge + level hints on
log(salary), MAE 524 USD, 27% overestimated by >30%** (experiment log rows 14 and 18).
Live now: `model_v0` (the two smart baselines). Live metric: _after release_.

## Architecture
```
Telegram channels (public pages) ─► collect (PII scrubbed) ─► raw_posts ─► dedupe
   ─► LLM extraction (labels only) ─► vacancies ─► train.py (one sklearn Pipeline)
   ─► models/model_vN.joblib + .json ─► web app ─► prediction_log ─► monitoring
```

## Data
Public Telegram IT job channels (`jobtracker/config.py`): 6,388 posts (2019 – Nov 2026), 5,122 after removing
reposts, 3,677 IT vacancies. Exploration: `notebooks/eda.ipynb`. Phone numbers, e-mails, @usernames, links and
contact-person names are removed before anything is stored; job-seeker posts are never stored.
An LLM turns each post into structured fields (`jobtracker/extract/schema.py`); it is used for data
cleaning only, never for the predictions the app serves.

## How to run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env              # add GEMINI_API_KEY (free, aistudio.google.com/apikey)
python -m scripts.collect         # new posts (first time: --full --pages 150)
python -m scripts.extract         # structured fields + labels (resumable)
python -m pytest                  # data checks
python train.py --cv-only         # compare models (CV on train only)
python train.py                   # save the best as models/model_vN.joblib + .json
python app.py                     # http://127.0.0.1:8000  (/dashboard, /monitor)
python retrain.py                 # after release: v2 candidate + promotion gate
python -m scripts.weekly          # weekly job: collect + extract (cron on the server)
python -m scripts.worst_predictions --target salary --model smart_keyword_median   # error worksheet
jupyter notebook notebooks/eda.ipynb   # data exploration
```

Docs: `docs/experiment_log.md`, `docs/error_analysis_*.md`, `docs/decision_note.md`,
`docs/release_checklist.md`, `docs/model_card_v1.md`, `docs/monitoring_report.md`, `docs/swap_and_break.md`,
`docs/architecture.pdf`.

## How to deploy
**Where it runs:** a Google Cloud **e2-micro** VM (always-free tier: 1 GB RAM, 30 GB standard disk,
region us-central1), Ubuntu 24.04. `gunicorn` serves the app, `systemd` keeps it running, `Caddy`
gives HTTPS on a free `<ip>.sslip.io` address, `cron` runs the weekly job. Files: `deploy/`.

**First setup (once)**
1. Google Cloud console → Compute Engine → **Create instance**: machine type `e2-micro`, region
   `us-central1` (or us-west1 / us-east1, the free ones), boot disk **Ubuntu 24.04, Standard
   persistent disk, 30 GB**, firewall: tick **Allow HTTP** and **Allow HTTPS**.
2. VPC network → IP addresses → make the VM's external IP **static** (the link never changes).
3. Click **SSH** next to the VM, then:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/kar1mov-u/ML-final/main/deploy/setup_server.sh | sudo bash
   sudo nano /srv/jobtracker/.env                 # GEMINI_API_KEY=...  (secrets never go to git)
   ```
4. Upload the database (it is not in git): in the SSH window, ⚙ → **Upload file** → `data/jobs.db`, then
   ```bash
   sudo mv ~/jobs.db /srv/jobtracker/data/ && sudo chown jobtracker:jobtracker /srv/jobtracker/data/jobs.db
   sudo systemctl restart jobtracker && curl -s localhost:8000/health
   ```
5. Open the `https://…sslip.io` address the script printed, from a phone.

**Release a new model version**
```bash
python train.py --version v1 --final     # on a laptop: saves models/model_v1.* and sets models/LIVE
git add models && git commit -m "model v1" && git tag v1 && git push --tags
# on the server:
sudo bash /srv/jobtracker/deploy/update.sh       # git pull + packages + restart + health check
```
Later versions go through the promotion gate: `python retrain.py` (writes `models/LIVE` only if the
candidate wins; every decision is logged in `docs/promotion_log.md`).

**Weekly automation (cron, `deploy/crontab.txt`):** every Monday 06:00 `scripts/weekly.py` collects
new posts (Telegram + hh.uz), labels them with Gemini and, after the v1 release, runs `retrain.py`.
A candidate is promoted only if it beats the live model on the newest week; every decision goes to
`docs/promotion_log.md`, and the app switches to a promoted model on the next request (no restart).
Models promoted on the server are created there: copy them back and commit them
(`scp server:/srv/jobtracker/models/model_v* models/ && git add models`) so they stay versioned.

**Roll back to the previous model:** `echo v0 > models/LIVE` (the app picks it up on the next request; restarting also works)
(all model files stay in git, so any version can be served again). `/health` shows the live version.

**What happens on restart:** systemd starts the app again within 3 seconds after a crash and on
every boot. The database is a file on the server disk (`data/jobs.db`), so predictions, labels and
posts survive restarts and deploys; cron also keeps a daily backup copy.

**Alternative:** `Dockerfile` (see the comment at its top); mount `./data` as a volume so the
database survives new images.

## What we learned
_TBD_

## Team
_TBD: names and who did what._
