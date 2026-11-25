# ML Final Project — Working Guide

Source of truth: `ML_Final_Project_Handbook.pdf` (Fall 2026–2027, 23 pages). If anything here conflicts with the handbook, the handbook wins.

## The one-line goal
Build a **small ML service for a real user**, release it at the start of **week 13**, and run it on live traffic until the demo.
**The model stays simple; the software around it is real.** Grades reward a correct workflow, a working system and honest analysis, *not* the highest score.

## Chosen project: #5 IT job market tracker & salary estimator
Work plan and task status: **`PLAN.md`** (update checkboxes as tasks finish).

- **Client / users:** career centre; students looking for IT jobs in Uzbekistan
- **Targets:** level (junior/middle/senior) classification; salary (USD/month) regression on posts that state one
- **Offline metrics:** level macro F1; salary MAE. **Live metric:** error on each new week's postings
- **Dummy:** most frequent level / median salary. **Smart baseline:** median salary per title keyword; keyword → level rule
- **Course models:** MultinomialNB + LogReg (level); LinReg + kNN + DecisionTree (salary)
- **Split:** by date (latest weeks = test), duplicate groups never cross the split

### Design decisions (keep consistent)
- **Data:** public Telegram IT job channels via `t.me/s/<channel>` **+ hh.uz vacancy pages** (instructor approved web scraping of hh, 2026-11). hh API is closed to anonymous use. hh scraper rules (`jobtracker/collect/hh_web.py`): ids come from hh's vacancy search for IT roles, the ONLY query-string URL (robots.txt disallows `*?*` in general; hh gave written permission 2026-11-22, `docs/hh_permission.md`), plus past ids from the Wayback Machine index; ≥3 s delay; honest User-Agent, never spoofed; stop on 403/429/captcha, never bypass. Logged out, hh search shows only *active* vacancies.
- **LLM (Google Gemini API, free tier, `gemini-3.5-flash-lite`) = data cleaning only:** extracts structured fields/labels from raw posts into the DB (structured outputs, 10 posts per request, resumable). Only PII-scrubbed text is sent (free-tier data may be used by Google). It never makes the served prediction.
- **Serving uses raw text → sklearn Pipeline only.** No LLM call at serving time (avoids training–serving skew and outside dependency).
- **Leakage guard:** strip salary amounts/currency from input text before training and serving.
- **Store** `raw_text`, `extracted_json`, `llm_model`, `prompt_version` per post; dedupe before extraction (never pay twice).
- **Validate LLM labels:** hand-label ~100 posts, report agreement.
- One documented rule each for: currency → USD, "from X" salaries, level source.

---

## Hard rules (never break these)
1. **Team**: pair, max 2 students. Both partners must show work in git history and the experiment log.
2. **Real users**: at least **10 people outside the pair** use the service before the demo.
3. **Tools**: pandas + scikit-learn for the model; course starter repo for app, DB and training script; hosting we set up ourselves.
4. **Models**: course models only — linear/logistic regression, kNN, decision trees, Naive Bayes, k-means. Anything else is an optional extra and never replaces the required comparison.
5. **Comparison**: at least **2 course models** vs a **dummy baseline** vs the **smart baseline** from the brief.
6. **Test discipline**: set aside the test split **on day one**. Do not look at it until release. Model selection = **cross-validation on train only**. Test score computed **once**, written into `model_v1.json`.
7. **Correct split for the project**: by **date / person / writer / group** — never a naive random split when data has time or group structure. No leakage.
8. **Release**: `v1` is git-tagged and frozen. Improvements go into a **v2 candidate** that replaces v1 **only if it beats v1 on the same held-out data** (promotion gate).
9. **Data ethics**: tell users what is logged and why. Collect by hand or with permission, follow site terms. Never store names, phone numbers, card numbers or other personal data we don't need.
10. **Secrets** (bot tokens, API keys) in environment variables, **never in git**.

## What we must ship (Required)
- [ ] `train.py` — rebuilds the model **from the database in one command**, using **one scikit-learn `Pipeline`**
- [ ] Versioned model + metrics file: `model_v1.joblib`, `model_v1.json`
- [ ] Bot / web app / API that loads the model and answers real users, and shows the model version
- [ ] **Prediction log**: `time` (Tashkent time), `input` (anonymised), `prediction`, `confidence`, `model_version`, `label` (filled later), `label_time`
- [ ] **Input checks**: empty / wrong-type / out-of-range input → clear message, never a crash
- [ ] Deployed on our own hosting: reachable from a phone, **auto-restarts** after crash/reboot
- [ ] README a stranger can use to run and redeploy (incl. deployment note)

## Advanced (extra credit / strengthens rubric)
- Feedback capture (buttons, corrections, real outcomes) stored as labels
- Retraining script with **promotion gate**
- Monitoring page: live metric over time, prediction counts, out-of-distribution inputs
- Dockerfile + ≥3 automated tests (data check, model smoke test, input-check test)

## Hosting requirements
- Reachable from start of week 13 until the demo; **HTTPS** (mandatory for Project 7)
- Auto-restart after crash or reboot; **database persists across restarts/deploys**
- Cost zero or within a limit agreed with the instructor
- Check pitfalls: free tiers that **sleep** (polling Telegram bots need an always-on process or a webhook), platforms that **wipe disk** (SQLite lost), monthly hour/memory limits covering weeks 10–15
- **Deployment note** in README: where it runs, how to deploy a new version, how to **roll back** to the previous model, what happens on restart. Test each step once before the week-10 checkpoint.

## Seven practices
1. **Client brief** → target, metric, cost of mistakes
2. **Baseline first** → dumb model running end-to-end *inside the app* before real modelling
3. **Experiment log** → every run, including failures (never delete rows)
4. **Error analysis** → 20 worst mistakes → fix the data or the model
5. **Release & monitor** → ship v1, log every prediction, compare live vs offline
6. **Feedback loop** → user corrections become labels; v2 promoted only if it beats v1
7. **Swap & break** → another pair attacks our service; we explain each failure

## Timeline (weeks 9–15, one checkpoint per week)
| Week | Milestone | Checkpoint to submit |
|---|---|---|
| 9 | Pick project, meet client, start collecting data, choose hosting | Data plan, first 50 rows, hosting plan (½ page) |
| 10 | Deploy starter app on our hosting; dummy + smart baselines; `train.py` saves versioned model + metrics | Live link, baseline results, `train.py` |
| 11 | Deployed app serves baseline & logs every prediction; error analysis round 1 | Prediction log from live app, error worksheet 1 |
| 12 | One `Pipeline` in `train.py`; CV; experiment log ≥5 runs; beta test with classmates; restart test | Pipeline, experiment log, beta feedback, deployment note |
| 13 | **Release v1 on day 1** (`git tag v1`); monitoring page; decision note | Release checklist + live link |
| 14 | Live traffic; feedback → labels; train v2, promote only if it beats v1; swap-and-break lab | Monitoring report, v2 decision, swap-and-break report |
| 15 | Final report, README, live demo, viva | Final submission |

## Templates to keep in the repo (graders look for each)
- **Experiment log** (from wk 10): `# | Date | What changed | Why | CV score | Kept?` — rows 1 = dummy, 2 = smart baseline. CV scores only, never test.
- **Error-analysis worksheet** (wk 11 & 13): 20 worst validation predictions — `Example ID | True | Predicted | Error | Cause | Note`. Causes: wrong label, missing feature, rare case, typo/outlier, duplicate/leakage, other. Most common cause decides next step.
- **Decision note** (wk 13, ½ page): metric & threshold and why; data fix tried + effect; model change tried + effect; what the learning curve says; what ships as v1.
- **Release checklist** (wk 13 day 1): train.py rebuilds & saves v1 files; test score computed once in `model_v1.json`; app shows version; every prediction logged; bad inputs handled; users told what's logged; `v1` tag pushed and live from phone; experiment log current.
- **Model card** (per release): what/for whom; training data (sources, rows, date range); offline results (baselines + models, CV + test); known weaknesses; what's logged and who sees it.
- **Monitoring report** (wk 14, 1 page): users & predictions per day; live vs offline metric and why they differ; unusual inputs; v1 vs v2 on same held-out data and which was promoted.
- **Swap-and-break report** (wk 14): `# | Input tried | Expected | Model's answer | Why it failed | Owners' response`.

## Final report structure
1. Client problem & framing (target, metric, cost of mistakes)
2. Data: sources, collection, cleaning, ethics
3. Baselines and models (2–3 sentences each)
4. Offline results table: dummy, smart, each model — CV and test
5. Error analysis & changes (data or model) with effect of each
6. System: architecture diagram; serving, logging, retraining
7. Live results: users, predictions, live vs offline, v2 decision
8. Swap-and-break findings & responses
9. Limitations & next steps
10. Who did what

## README structure
`# Title` (one sentence + live link) → `## Result` (best model vs baselines table, live metric) → `## Architecture` (diagram: data source, DB, train.py, model registry, app, prediction log, monitoring) → `## Data` → `## How to run` (`pip install -r requirements.txt`, `python train.py`, `python app.py`) → `## How to deploy` → `## What we learned` (3 bullets) → `## Team`.

## Grading — 50 pts (50% of course)
| Rubric | Criterion | Pts | Full marks when |
|---|---|---|---|
| **SO1 Problem solving (16)** | Problem understanding | 5 | Clear target, metric, cost of mistakes; decision note justifies them |
| | Model choice | 4 | ≥2 course models vs dummy + smart baselines; released model justified for client |
| | Evaluation | 5 | CV for choices; test used once; live next to offline; v2 follows promotion gate |
| | Limitations | 2 | Offline/live gap, swap-and-break failures, data limits explained honestly |
| **SO6 Technical (20)** | Python skills | 7 | Notebook and `train.py` run from scratch; pandas/sklearn used correctly |
| | ML pipeline | 4 | One `Pipeline`, right split (date/person/writer/group), no leakage |
| | Deployment | 3 | Own hosting, phone-reachable, restarts, DB persists, secrets out of git, every prediction logged |
| | Feedback loop | 2 | Feedback stored as labels, models versioned, v2 through promotion gate |
| | Code readability | 4 | Readable, commented code; README + deployment note a stranger can follow |
| **SO3 Communication (10)** | Clarity | 4 | Report follows structure, results tables, plain explanations |
| | Organisation | 3 | All templates complete |
| | Presentation & viva | 3 | Live demo within time; **both** students can explain any part |
| **SO5 Teamwork (4)** | Shared contribution | 2 | Log + git history show both partners |
| | Participation | 1 | Checkpoints on time |
| | Responsibility | 1 | Each explains own part in viva |

**Does NOT lose marks:** live metric below offline (if explained); v2 failing the gate and not released; smart baseline beating our model (if reported honestly).
**LOSES marks:** checking the test set repeatedly; train/test leakage; deleting failed runs; service down at demo **with no recorded backup video**; results nobody in the pair can explain.

---

## The 8 project options (quick reference)
| # | Project | Task | Offline metric | Dummy | Smart baseline | Course models | Split / key trap | Difficulty |
|---|---|---|---|---|---|---|---|---|
| 1 | Tashkent smog alert (Telegram channel + page) | Regression PM2.5 + unhealthy flag | MAE µg/m³; recall on unhealthy days | Median | Persistence (tomorrow = today) | LinReg, kNN, DT; LogReg for flag | By date; only data known the evening before; UTC vs Tashkent time; missing hours | Easiest |
| 2 | Spam/scam guard for group chats | Binary text clf | Precision/recall on spam (≥90% precision) | Most frequent | Link + money/urgency keyword | MultinomialNB, LogReg, kNN | Template copies same side; normal msgs with links; base-rate effect; never auto-delete in v1 | Medium |
| 3 | Campus helpdesk router | Text clf (office) + kNN retrieval | Macro F1; top-3 retrieval acc | Most frequent office | Keyword rules per office | MNB, LogReg; kNN cosine on TF-IDF | Paraphrases same side; similarity threshold on validation; uz/ru/en | Medium–hard |
| 4 | Canteen demand forecaster | Regression portions/dish/day | MAE overall & per dish | Median per dish | Same weekday last week | LinReg, kNN, DT | By date; new dish fallback; sold-out = hidden demand | Medium |
| 5 | IT job tracker & salary estimator (hh.uz) | Level clf + salary regression | Macro F1; salary MAE | Median / most frequent | Median salary by title keyword | NB, LogReg; LinReg, kNN, DT | Dedupe before split; currencies; hidden salaries bias | Medium |
| 6 | Expense categorizer bot | Multi-class text clf | Macro F1; per-category acc | Most frequent | Merchant lookup | MNB, LogReg, kNN | Store only amount/merchant/category/date; evaluate unseen merchants separately; `/delete_my_data` | Medium |
| 7 | Live activity tracker (phone motion) | Multi-class, 2–3 s windows | Macro F1 split by person | Most frequent | Movement-strength threshold | kNN, DT, GaussianNB | Split by person; sampling rates differ; HTTPS required; train on own page's data | Easy ML, hard software |
| 8 | Handwritten score reader + human review | Digit clf with confidence threshold | Accuracy split by writer | Most frequent | NearestCentroid | kNN, LogReg, DT | Split by writer; identical preprocessing (8×8); threshold on validation; ≥99% on auto-accepted | Medium |

## How Claude should work on this project
- Always keep the **test split untouched** until release; use CV on train for every comparison.
- Every experiment → append a row to the experiment log (never delete rows).
- Keep everything in **one sklearn `Pipeline`** inside `train.py`; models saved as `model_vN.joblib` + `model_vN.json`.
- Prefer simple, readable, commented code over clever code — both partners must be able to explain it in the viva.
- Never commit secrets; never store personal data beyond what's needed.
- Be honest in analysis: report when a baseline wins or live metric drops, and explain why.
