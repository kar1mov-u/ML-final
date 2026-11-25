# Week 9 checkpoint: data plan and hosting plan

## Client brief → ML task
- **Client:** university career centre. **Users:** students looking for IT jobs in Uzbekistan.
- **Request:** "Estimate the level and salary of any job posting, and give us a weekly view of what the market wants."
- **Targets:** (1) level: junior / middle / senior (classification); (2) salary in USD per month (regression, on posts that state one).
- **Metrics:** level: macro F1; salary: MAE in USD. **Live metric:** the same errors on each new week's postings.
- **Cost of mistakes:** overestimating salary sets false expectations for students, so we report MAE plus the share of posts overestimated by more than 30%. Calling a senior role junior wastes applications. Both errors matter, so we use macro F1 rather than accuracy.

## Data source (changed from the brief, needs instructor OK)
The brief names the hh.uz API. HeadHunter now refuses anonymous API requests (`403 forbidden`), so
we collect from **public Telegram IT job channels** through their public web pages (`t.me/s/<channel>`),
which anyone can open without logging in. We have also applied for an hh API token as a later bonus source.

| Channel | Content | Notes |
|---|---|---|
| uzdev_jobs | IT vacancies, ru/uz | often $ salaries |
| uzpythonjobs | Python vacancies | low volume |
| click_jobs | Clickjobs aggregator | also non-IT jobs → filtered by `is_it_job` |
| UstozShogird | IT community board | employer posts only ("Xodim kerak") |
| it_jobs_uz | IT vacancies | |
| itvakansiyalar | IT vacancies | low volume |

**Collection:** one request every 1.5 s, honest User-Agent, incremental (weekly runs only fetch new posts).
**Rows collected so far:** see "Numbers" below.

## Cleaning and labels
1. **Privacy first:** phone numbers, e-mails, @usernames, links and contact-person names are removed
   *before* storage. Job-seeker posts (a person advertising themselves) are never stored.
2. **Duplicates:** reposts are grouped (same text hash, or TF-IDF cosine ≥ 0.90). A group always
   stays on one side of the train/test split.
3. **Structured fields:** an LLM (Google Gemini 3.5 Flash-Lite, free tier, structured JSON output) reads each post and returns
   title, level, salary, currency, skills, language, `is_it_job`. It is a cleaning step only; the
   served model is scikit-learn on the raw text.
4. **Label rules (fixed):**
   - *Level:* the level named in the title/text wins; otherwise experience (<1 y junior, 1–3 y middle, 3+ y senior); else unknown (excluded from level training).
   - *Salary → USD/month:* range → midpoint; "from X" → X; "up to Y" → Y; fixed rates (12 500 UZS, 90 RUB, 0.92 EUR per USD); outside 100–20 000 → treated as missing.
5. **Label quality check:** both partners hand-label 50 posts each; we report LLM agreement per field.
6. **Leakage guard:** salary amounts and currency words are removed from the model input text.

## Split
By date: the most recent weeks form the test set, frozen on day one. Model choice uses
time-ordered cross-validation on the training part only.

## Known risks
- Many posts hide the salary → the salary model only learns from posts that show one; we compare them with the rest.
- Channel mix changes over time (more non-IT posts in aggregators).
- Posted salaries are not paid salaries; Telegram channels are not the whole market.

## Hosting plan (to decide)
Requirements: always-on process (weekly cron + web app), persistent disk for SQLite, HTTPS, free or cheap,
auto-restart. Candidates:

| Option | Always on | Persistent disk | HTTPS | Cost | Notes |
|---|---|---|---|---|---|
| Small VPS (Hetzner / DigitalOcean) + Caddy + systemd | yes | yes | Caddy auto-TLS | ~$4–6/mo | most control; we run updates ourselves |
| Fly.io / Railway with a volume | yes (paid tier) | volume | built-in | small fee | easy deploys; check free-tier sleep and limits |
| Oracle Cloud free tier VM | yes | yes | via Caddy | free | sign-up can be slow |
| Render free tier | **sleeps** | **disk wiped** | yes | free | ❌ fails two requirements |

Recommendation: a small VPS with Docker (restart policy `unless-stopped`) or systemd, Caddy for HTTPS,
SQLite on the server disk with a nightly backup copy.

## Numbers (first backfill, 2026-11-14)
| Channel | Posts | Unique (after dedupe) | From | To |
|---|---|---|---|---|
| uzdev_jobs | 2 988 | 2 229 | 2022-05 | 2026-11 |
| click_jobs | 1 575 | 1 402 | 2023-06 | 2026-11 |
| uzpythonjobs | 683 | 565 | 2019-10 | 2026-10 |
| it_jobs_uz | 656 | 585 | 2019-02 | 2026-09 |
| UstozShogird | 476 | 423 | 2026-03 | 2026-11 |
| itvakansiyalar | 10 | 10 | 2026-05 | 2026-11 |
| **Total** | **6 388** | **5 122** | | |

- Posts per year: 2019: 133 · 2020: 263 · 2021: 391 · 2022: 808 · 2023: 1 052 · 2024: 1 125 · 2025: 1 309 · 2026: 1 307
- About 62% of unique posts mention a currency, so they may state a salary (an upper bound; the LLM extraction gives the real count).
- Share of non-IT and non-job posts: known after extraction (`is_it_job`, `is_job_post`).
- Privacy check after scrubbing: 0 posts with phone numbers, e-mails or links left.
- First 50 rows: `docs/first_50_rows.csv`.
