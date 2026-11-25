# Project Plan — Uzbekistan IT Job Market Tracker & Salary Estimator (Project 5)

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done
Owner: **A** / **B** (partner split — both must show commits + experiment-log rows, SO5 teamwork)

> Rule of thumb: every phase ends with something **running end-to-end**. Baseline in the app first, real models later.

---

## Architecture (target)
```
Telegram channels (public t.me/s pages) ─► PII scrub ─► dedupe ─► raw_posts
                                                      │ new rows only
                                                      ▼
                              LLM extraction (Gemini free tier, JSON schema, 10 posts per request)
                                                      ▼
                         vacancies: raw_text + level + salary_usd + skills + flags
                                                      ▼
   train.py: strip salary from text → TF-IDF → NB / LogReg (level) | LinReg / kNN / DT (salary)
                                                      ▼
         models/model_vN.joblib + model_vN.json ─► web app (raw text in, NO LLM at serving)
                                                      ▼
                       prediction_log ─► monitoring page ─► weekly retrain + promotion gate
```

---

## Phase 0 — Setup & decisions (do first, ~1 day)
- [ ] **0.1** Message instructor: hh API now needs a token → we use public Telegram IT job channels (+ hh token if approved). Get OK. *(A)*
- [ ] **0.2** Apply for hh API app at dev.hh.ru as a bonus source. *(A)*
- [ ] **0.3** Get Telegram `api_id` / `api_hash` at my.telegram.org. *(B)*
- [ ] **0.4** Get Anthropic API key; decide extraction model (Opus 5.5 vs Haiku 5.5 — test both on 0.7 sample). *(B)*
- [~] **0.5** Create git repo (GitHub), add starter repo code, `.gitignore` (`.env`, `*.db`, `models/*.joblib` if large), `.env.example`. *(A)*
- [ ] **0.6** Pick hosting: always-on process, persistent disk/DB, HTTPS, free or cheap (candidates: Fly.io / Railway with volume, cheap VPS, Oracle free tier). Write ½-page hosting plan. *(B)*
- [x] **0.7** List 5–10 Telegram IT job channels (e.g. @UzDev_Jobs, @uzpythonjobs …); check each is public. *(A+B)*
- [x] **0.8** Fill "Chosen project" + design decisions in `CLAUDE.md`. *(Claude)*

**Checkpoint (wk 9):** data plan, first 50 rows, hosting plan.

## Phase 1 — Data collection (≈ 2–3 days)
- [x] **1.1** DB schema (SQLite or Postgres): `raw_posts`, `vacancies`, `prediction_log`, `extraction_runs`. *(A)*
- [x] **1.2** `collect/telegram_web.py` — public t.me/s pages (Telethon optional later): pull full history of each channel, store `channel, msg_id, date, raw_text`; skip already stored `(channel, msg_id)`. *(B)*
- [~] **1.3** hh.uz scraper `jobtracker/collect/hh_web.py` + `scripts/collect_hh.py` (hh search for IT roles → vacancy pages, robots-checked, IT filter, `hh_meta` with structured salary; parsing in `hh_parse.py`). Run `--probe`, then the full crawl. *(A)*
- [x] **1.4** Dedupe: exact `(channel,msg_id)` + near-duplicate text (normalized hash / TF-IDF cosine > 0.9) → `dup_group_id`. *(A)*
- [x] **1.5** Export first 50 rows for the checkpoint. *(B)*

## Phase 2 — LLM extraction & labels (≈ 2–3 days)
- [x] **2.1** Define JSON schema (Pydantic): `is_job_post, is_it_job, title, level{junior,middle,senior,lead,unknown}, salary_min, salary_max, currency, salary_period, skills[], language`. *(B)*
- [x] **2.2** `extract/llm_extract.py` — `messages.parse()` with schema; store `extracted_json, llm_model, prompt_version`. Never re-extract a post already done. *(B)*
- [x] **2.3** Pack 10 posts per request + rate limiting + resumable runs (free-tier quota); same script for weekly new posts. *(B)*
- [~] **2.4** Hand-label ~100 posts (both partners, 50 each) → measure LLM agreement per field; record in report. *(A+B)* — sheet `docs/labels/hand_labels.csv` created (50 A / 50 B); fill it, then `python -m scripts.label_agreement`
- [x] **2.5** One salary-normalization rule: convert to USD/month (fixed documented rate), "from X" → rule (e.g. min=X, max=NaN, use min), drop absurd values. *(A)*
- [x] **2.6** Level label rule: LLM finds the named level + years, `final_level()` in code applies the rule (prompt v2); documented + tested. *(A)*
- [x] **2.7** EDA notebook: counts, salary distribution, % with salary, level balance, how salary-posts differ from no-salary posts (bias trap). *(A)* — `notebooks/eda.ipynb` (train only); finding: no-salary posts are 40% junior vs 9%

## Phase 3 — Split, baselines, app skeleton (≈ 2 days) — CHECKPOINT wk 10
- [x] **3.1** **Test split on day one, by date**: last N weeks = test, frozen. Dupe groups never cross the split. Save split boundary in config. *(A)* — `TEST_START = 2026-09-01` in config, `jobtracker/data.py`, tested
- [x] **3.2** Text cleaner: strip salary numbers/currency from input text (leakage). Unit-tested. *(B)*
- [x] **3.3** `train.py` v0: from DB → dummy (median salary / most-frequent level) → save `model_v0.joblib` + `model_v0.json` with CV metrics. *(A)* — `model_v0` saved (smart baselines), CV in `model_v0.json`
- [x] **3.4** Smart baseline: median salary per title keyword; keyword→level rule. Add to CV comparison. *(A)* — `KeywordLevelRule`, `KeywordSalaryMedian` in `jobtracker/models.py`
- [x] **3.5** Web app skeleton (starter repo): paste vacancy → validate input → predict level + salary range → show model version. *(B)* — Flask `app.py` + `templates/index.html`, JSON API, /health
- [x] **3.6** Input checks: empty, too short (<N words), non-IT/non-job text, absurd length → clear message. *(B)* — `predict.check_input`, tested
- [ ] **3.7** Deploy to chosen hosting; env vars for secrets; auto-restart (systemd/Docker restart policy/platform). Test: kill process → comes back; restart → DB still there. *(B)*
- [x] **3.8** Start `experiment_log.md` (rows 1–2: dummy, smart). *(A)* — rows 1–9 filled 2026-11-19

**Checkpoint (wk 10):** live link, baseline results, `train.py`.

## Phase 4 — Logging & error analysis 1 (≈ 2 days) — CHECKPOINT wk 11
- [x] **4.1** `prediction_log` written on every request: time (Tashkent), input summary, prediction, confidence, model_version, label, label_time. *(B)* — `predict.log_prediction`
- [x] **4.2** Tell users what is logged (notice on the page). *(B)* — notice on the page
- [x] **4.3** First real models in CV: MultinomialNB + LogReg (level); LinReg + kNN + DecisionTree (salary). *(A)* — CV run 2026-11-19, see experiment log rows 5–9
- [~] **4.4** Error worksheet 1: 20 worst validation predictions, cause per row, count causes → decide data vs model fix. *(A+B)* — worksheets generated (`scripts/worst_predictions.py` → `docs/error_analysis_*.md`); fill Cause column
- [ ] **4.5** Optional k-means on skills/TF-IDF for the dashboard ("job clusters") — uses the wk 11 topic. *(A)*

## Phase 5 — Pipeline, CV, beta (≈ 3 days) — CHECKPOINT wk 12
- [x] **5.1** Single sklearn `Pipeline` (ColumnTransformer: TF-IDF text + skills one-hot + numeric) inside `train.py`. *(A)* — FeatureUnion(TF-IDF + LevelHints) inside the Pipeline; log-target Ridge
- [x] **5.2** Time-aware CV (`TimeSeriesSplit` or grouped by week) on train only; ≥5 logged runs incl. failures. *(A)* — TimeSeriesSplit(5); experiment log rows 1–18 incl. failures
- [x] **5.3** Weekly dashboard page: top skills, salary by level, postings per week. *(B)* — `/dashboard` (postings per week, top skills, salary by level, last 12 weeks)
- [~] **5.4** Weekly job (cron): collect → extract → dedupe → store (retrain is manual/gated). *(B)* — `scripts/weekly.py` ready; add the cron line on the server
- [ ] **5.5** Beta test with classmates; collect feedback (form or buttons). *(A+B)*
- [~] **5.6** Restart test + write deployment note in README (where, deploy, rollback model, restart behaviour). *(B)* — deployment note in README + `deploy/`; restart test once the server exists

## Phase 6 — Release v1 (week 13, day 1)
- [ ] **6.1** Decision note (½ page): metric choice, data fix + effect, model change + effect, learning curve, what ships. *(A)*
- [ ] **6.2** Final `train.py` run → `model_v1.joblib`; **test set evaluated ONCE** → written into `model_v1.json`. *(A)*
- [ ] **6.3** Release checklist ticked; `git tag v1` pushed; live from a phone. *(B)*
- [ ] **6.4** Model card v1. *(A)*
- [x] **6.5** Monitoring page: predictions/day, live error per new week, out-of-distribution inputs (unknown skills, language, salary out of range). *(B)* — `/monitor`: predictions/day, corrections, live vs offline per new week (after release), odd inputs
- [ ] **6.6** Recruit ≥10 real users outside the pair (career centre, classmates, ML club). *(A+B)*

## Phase 7 — Live, v2, swap-and-break (week 14)
- [ ] **7.1** Each new week's postings = fresh labels; compute live metric vs offline. *(B)*
- [x] **7.2** Optional feedback buttons ("level looks wrong" / actual salary) → labels. *(B)* — feedback form under each result → `prediction_log.label`
- [x] **7.3** `retrain.py` with **promotion gate**: v2 replaces v1 only if better on the same held-out latest week. Log decision either way. *(A)* — `retrain.py`: latest week held out, user corrections added, `models/LIVE` only if better; `docs/promotion_log.md`
- [ ] **7.4** Monitoring report (1 page). *(A)*
- [ ] **7.5** Swap-and-break lab: attack another pair; answer attacks on ours (non-IT post, English post, absurd salary, 3-word description). *(A+B)*
- [x] **7.6** Advanced (if time): Dockerfile + ≥3 tests (data check, model smoke, input check); "skills linked to higher pay" from LinReg coefficients (correlation ≠ cause). *(A/B)* — Dockerfile (built + health-checked), 17 tests, `scripts/skill_pay.py` → `docs/skills_and_pay.md`

## Phase 8 — Final submission (week 15)
- [ ] **8.1** Final report (10-section structure from CLAUDE.md). *(A+B)*
- [ ] **8.2** README per template; stranger can run & redeploy. *(B)*
- [ ] **8.3** Record backup demo video (service down at demo without video = lost marks). *(A)*
- [ ] **8.4** Viva prep: each partner can explain every part, not just their own. *(A+B)*

---

## Risks & mitigations
| Risk | Mitigation |
|---|---|
| Too few posts with salary | Pull more channels / longer history; report salary coverage honestly |
| LLM label errors | Hand-check 100; "wrong label" cause in error analysis |
| Reposts across channels leak into test | Dedupe groups before split, split by date |
| Leakage: salary in input text | Strip salary in cleaner, unit test it |
| LLM API down / cost | Serving never calls LLM; extraction cached; free tier, resumable |
| Hosting sleeps / wipes disk | Choose always-on + persistent volume; test restart in wk 10 |
| Demo outage | Backup video |
