# Uzbekistan IT Job Market Tracker
Estimates the level (junior / middle / senior) and monthly salary of an IT job posting in Uzbekistan,
and shows a weekly view of the skills employers ask for. Built for students and the career centre.

Live link: https://web-production-64885b5b.up.railway.app  (also `/dashboard`, `/monitor`)

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
**Where it runs:** [Railway](https://railway.com), project `it-job-estimator`, service `web`.
Railway builds the `Dockerfile`, runs `gunicorn` (1 worker, 4 threads) and gives HTTPS on
`*.up.railway.app`. A **volume** is mounted at `/app/data`: it holds the database (`jobs.db`) and the
models (`models/`), so both survive restarts and redeploys. Secrets are Railway variables, never in git.

| Variable | Value | Why |
|---|---|---|
| `GEMINI_API_KEY` | (secret) | weekly label extraction |
| `DB_PATH` | `/app/data/jobs.db` | database on the volume |
| `MODELS_DIR` | `/app/data/models` | models on the volume (git models are copied in at start-up) |
| `WEEKLY_JOB` | `on` | the app runs `scripts/weekly.py` every Monday 06:00 Tashkent time |

**First setup (done once, 2026-11-26)**
```bash
railway login
railway init --name it-job-estimator
railway add --service web --variables "DB_PATH=/app/data/jobs.db" --variables "MODELS_DIR=/app/data/models" --variables "WEEKLY_JOB=on"
railway service link web
railway variables --set "GEMINI_API_KEY=..."
railway volume add --mount-path /app/data
railway up --detach                                   # build + deploy from this folder
railway volume files --volume web-volume upload --overwrite jobs.db jobs.db   # the DB is not in git
railway domain                                        # public HTTPS link
```

**Deploy a new version (code or model)**
```bash
python train.py --version v1 --final     # release only: saves models/model_v1.* and sets models/LIVE
git add models && git commit -m "model v1" && git tag v1 && git push --tags
railway up --detach                      # new image; v1 is copied onto the volume and served
```
After the release, the weekly job retrains inside the app; a candidate is promoted only if it beats
the live model on the newest week (`retrain.py`, decisions in `docs/promotion_log.md`). A model
promoted on the server lives on the volume; to keep it in git:
`railway volume files --volume web-volume download models/model_v2.joblib models/` (same for `.json`).

**Roll back to the previous model:** set the variable `MODEL_VERSION=v0` in Railway (it overrides
`models/LIVE`); the service redeploys and `/health` shows the version. Remove it to go back.

**What happens on restart:** Railway restarts the container after a crash or a redeploy. The
database and models are on the volume, so posts, predictions and labels survive. Tested
2026-11-26: logged a prediction, restarted the service, the prediction was still there.

**Backup:** `railway volume files --volume web-volume download jobs.db backup-jobs.db`

**Alternative:** any Linux server with `deploy/setup_server.sh` (systemd + Caddy + cron), or plain
Docker (see the comment at the top of the `Dockerfile`).

## What we learned
_TBD_

## Team
_TBD: names and who did what._
