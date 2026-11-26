# Prep: questions, models, data, training

Short answers for the instructor. Numbers as of 2026-11-26.

---

## 1. What questions does the service answer?

A student pastes an IT job vacancy and gets two answers:

| Question | ML task | Metric | Why this metric |
|---|---|---|---|
| **"Is this job junior, middle or senior?"** | Classification, 3 classes | **Macro F1** | Levels are unbalanced (middle 57%, junior only 15%). Accuracy would reward always saying "middle"; macro F1 counts each level equally. |
| **"How much does it pay per month?"** | Regression, USD/month | **MAE in USD** + share **overestimated by >30%** | MAE is easy to explain ("off by $524 on average"). Overestimating is the costly mistake: it gives students false expectations, so we track it separately. |

Plus a **weekly market dashboard** (no model): postings per week, top skills, median salary by level.
That is the client's second request: "a weekly view of what the market wants".

**Client:** university career centre. **Users:** students looking for IT jobs in Uzbekistan.
**Live metric:** the same two errors on each new week's vacancies; every week is a fresh test set.

---

## 2. What data do we have?

| Source | How | Posts | Dates |
|---|---|---|---|
| Public Telegram IT job channels (6) | Public web pages `t.me/s/<channel>`, 1.5 s between requests, honest User-Agent | 6,414 | 2019-02 → 2026-11 |
| hh.uz vacancy pages | Scraper, ≥3 s delay, stops on block; instructor + hh permission (`docs/hh_permission.md`) | 1,570 | 2024-02 → 2026-11 |

From raw posts to training rows:

```
7,984 posts ─► remove personal data (phones, e-mails, @users, links, names) BEFORE storing
           ─► remove reposts (same text or ≥90% similar) ─► 6,679 unique
           ─► Gemini reads each post → title, level, salary, currency, skills, is_it_job
           ─► 4,375 real IT vacancies (non-IT and non-job posts are dropped)
```

**Why an LLM?** Posts are messy: Uzbek/Russian/English, "1.5 mln so'm", "от 2000$", emoji.
Gemini turns them into the same fields every time (structured JSON). **It only cleans the data
and makes labels; it never makes the prediction users see.**

**Label rules (fixed, documented):**
- **Level:** the level named in the post wins; otherwise years asked for (<1 junior, 1–3 middle,
  3+ senior); otherwise "unknown" and the post is left out. Intern counts as junior, lead as senior.
- **Salary → USD/month:** range → midpoint; "from X" → X; "up to Y" → Y; fixed rates
  (12,500 UZS, 90 RUB, 0.92 EUR per USD); per year ÷12, per hour ×168; outside $100–$20,000 → missing.

**Label quality:** both of us hand-label 100 random posts and report agreement with Gemini.

---

## 3. Which models?

Every model is **one scikit-learn Pipeline**: `text → remove salary numbers → features → model`.

**Level** (cross-validation macro F1)

| Model | Score | |
|---|---|---|
| Dummy: always "middle" | 0.24 | required baseline |
| Smart baseline: level word in text, else years | 0.75 | the rule to beat |
| Naive Bayes (TF-IDF words) | 0.35 | course model |
| Logistic regression (TF-IDF words) | 0.57 | course model |
| Naive Bayes + 7 hints | 0.70 | |
| **Logistic regression + 7 hints** | **0.83** | **best → v1 candidate** |

**Salary** (cross-validation MAE in USD)

| Model | MAE | Overestimated >30% | |
|---|---|---|---|
| Dummy: median salary | 711 | 33% | required baseline |
| Smart baseline: median salary per job-title keyword | 698 | 33% | the rule to beat |
| Linear regression (Ridge) | 571 | 39% | course model |
| kNN (10 most similar posts) | 622 | 39% | course model |
| Decision tree | 655 | 37% | course model |
| kNN + hints | 580 | 35% | |
| **Ridge + hints, learns log(salary)** | **524** | **27%** | **best → v1 candidate** |

**The 7 hints:** yes/no answers to "mentions senior / middle / junior?" and
"asks for no years / <1 / 1–3 / 3+ years?". They give the model the two strongest clues directly.

**Live now:** `v0` = the two smart baselines (handbook: baseline in the app first).
**v1 at release (week 13):** the two best models above.

---

## 4. How do we train?

```
database (4,375 unique IT vacancies)
   │
   ├── split BY DATE, fixed on day one:
   │      train = posted before 2026-09-01   → 3,421 (2,610 with level, 3,163 with salary)
   │      test  = posted from 2026-09-01     →   954  (locked until release, used ONCE)
   ▼
5-fold TimeSeriesSplit on train only: learn on older posts, check on the next newer ones
   ▼
compare all models above → pick the best
   ▼
refit on all train rows → save models/model_vN.joblib + model_vN.json (metrics, data info)
```

One command: `python train.py`. Release: `python train.py --version v1 --final` scores the test set
once, writes it into `model_v1.json`, and refuses to run a second time.

**After release (feedback loop):** users can correct a prediction (stored as a label). Each week
`retrain.py` trains a v2 candidate on newer posts + corrections; it replaces v1 **only if it beats v1
on the same latest week** (promotion gate). Every decision is logged in `docs/promotion_log.md`.

---

## Likely follow-up questions

**Why split by date, not randomly?** Jobs are posted over time and reposted. A random split would put
reposts and "future" posts in training, so the scores would look better than real life. By date,
the model is tested like in reality: trained on the past, used on new posts. Reposts are grouped
first, so a group never sits on both sides.

**How do you stop leakage?** (1) Salary numbers and currency words are removed from the text before
training and serving, so the salary model can't read the answer (unit-tested; 0 of 3,418 salary
posts still show a currency word). (2) Date split + repost groups. (3) The test set is untouched
until release.

**Isn't the level just written in the text?** Partly yes, and we report it honestly. The label comes
from the level word or years, so for 90% of posts the answer is in the text and the model mostly
"reads" it. On the 250 posts that state neither, the real guessing case, LogReg scores about 0.55–0.59
and the keyword rule only 0.18. We will report scores split into these groups. This is not leakage: the
user pastes the same text into the app, so the clue is really available when predicting.

**Posts without a salary?** Only salary-stating posts train the salary model. The notebook shows
the hidden-salary posts are 40% junior vs 9% of the others, so the model sees few juniors and may
overestimate junior pay. That's why we track the ">30% overestimated" share.

**Why Ridge and not plain linear regression?** Plain linear regression with thousands of word
features overfits badly (more features than posts). Ridge is linear regression with a penalty that
keeps the weights small. Learning log(salary) handles skewed salaries and cuts overestimates.

**Why trust Gemini's labels?** We store the full LLM answer, the model name and the prompt version
for every post, and we check 100 posts by hand. Disagreements go into error analysis as "wrong label".

**Limitations:** Telegram + hh is not the whole market; posted salary ≠ paid salary; 811 train posts
have no level label at all (left out); fixed exchange rates; hh posts are almost all in the test period,
so they only help training after release.
