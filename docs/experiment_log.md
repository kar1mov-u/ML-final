# Experiment log

One row per run. **Never delete a row**, including failed runs. Scores are cross-validation on the
training part only (split by date); the test set is used once, at release.

| # | Date | Target | What changed | Why we tried it | CV score | Kept? | Who |
|---|------|--------|--------------|-----------------|----------|-------|-----|
| 1 | 2026-11-19 | salary | Dummy baseline (median) | Reference point | MAE 712, over30 33% | Yes (reference) |  |
| 2 | 2026-11-19 | salary | Smart baseline: median salary per title keyword | The rule to beat | MAE 694, over30 31% | Yes, in v0 |  |
| 3 | 2026-11-19 | level | Dummy baseline (most frequent level) | Reference point | macro F1 0.236 | Yes (reference) |  |
| 4 | 2026-11-19 | level | Smart baseline: keyword → level rule | The rule to beat | macro F1 0.749 | Yes, in v0 |  |
| 5 | 2026-11-19 | level | MultinomialNB on TF-IDF (1–2 grams) | First course model | macro F1 0.349 | No (below rule) |  |
| 6 | 2026-11-19 | level | LogReg (balanced) on TF-IDF | Second course model | macro F1 0.556 | No (below rule) |  |
| 7 | 2026-11-19 | salary | Ridge (linear) on TF-IDF | Course model | MAE 573, over30 40% | Candidate: best MAE but overestimates more often |  |
| 8 | 2026-11-19 | salary | kNN (k=10, cosine) on TF-IDF | Course model | MAE 618, over30 38% | No |  |
| 9 | 2026-11-19 | salary | Decision tree (depth 8) on TF-IDF | Course model | MAE 666, over30 38% | No |  |
| 10 | 2026-11-19 | salary | Smart baseline searches the keyword in the title lines first (brief: "same job-title keyword") | Match the brief's definition | MAE 699, over30 33% (was 694 / 31%) | Yes, matches the brief; v0 rebuilt with it |  |
| 11 | 2026-11-19 | both | TF-IDF keeps 1-character tokens (`token_pattern`) | Error analysis: "3 years" lost its "3" | LogReg 0.556→0.576; NB 0.349→0.352; Ridge MAE 573→571 | Yes (small gain) |  |
| 12 | 2026-11-19 | level | TF-IDF min_df 2, 50k features | More vocabulary | LogReg 0.565, NB 0.310 (worse) | No |  |
| 13 | 2026-11-19 | level | LogReg + 7 level hints (level words + years bins), only the first level word flagged | Give the model what the rule sees | macro F1 0.770 | No: "Middle/Senior" lost one word |  |
| 14 | 2026-11-19 | level | LogReg + 7 level hints, every level word flagged, hints weight 3 | Fix of row 13 | **macro F1 0.825** (beats rule 0.749) | Yes: v1 candidate |  |
| 15 | 2026-11-19 | level | Naive Bayes + level hints (weight 3) | Same idea for NB | macro F1 0.695 (weight 1: 0.494) | No (below rule) |  |
| 16 | 2026-11-19 | salary | kNN + level hints | Seniority drives pay | MAE 581, over30 35% | No |  |
| 17 | 2026-11-19 | salary | Ridge + level hints | Seniority drives pay | MAE 539, over30 36% | Superseded by 18 |  |
| 18 | 2026-11-19 | salary | Ridge + level hints, trained on log(salary) | Salaries are skewed; overestimates are the costly error | **MAE 524, over30 27%** (beats smart 699 / 33%) | Yes: v1 candidate |  |
| 19 | 2026-11-22 | both | All candidates re-run from scratch on the bigger DB (Telegram + hh.uz): 4,375 IT vacancies, train 3,421 (2,610 level / 3,163 salary), test 954 untouched | New data source; check the ranking still holds | Level: dummy 0.236, rule 0.751, NB 0.354, LogReg 0.571, NB+hints 0.696, **LogReg+hints 0.826**. Salary MAE: dummy 711, smart 698, Ridge 571, kNN 622, tree 655, kNN+hints 580, **Ridge+hints log 524 (over30 27%)** | Same winners as rows 14 and 18; scores almost unchanged (train grew by only 20 rows: hh posts are almost all in the test period) |  |

Setup for rows 1–9: 3,401 train vacancies (2,590 with level, 3,157 with salary), 5-fold
`TimeSeriesSplit`, test = posts from 2026-09-01 (276, untouched). Saved as `model_v0` (rows 4 + 10).

## Data / label versions
| Date | Change | Effect |
|------|--------|--------|
| 2026-11-18 | Extraction prompt v2, model `gemini-3.5-flash-lite`; level rule applied in code (`final_level`) | first 20 posts: levels follow the rule consistently |
| 2026-11-19 | Full extraction: 5,122 posts (4,682 gemini-3.5-flash-lite, 440 fallback gemini-3.1-flash-lite) | 3,677 IT vacancies |
| 2026-11-19 | Leakage fix: `strip_salary` now removes so‘m / сўм / soums | 583 currency tokens leaked before, 0 after |
| 2026-11-22 | New source: hh.uz vacancy pages (`scripts/collect_hh.py`, sitemap → page, robots-checked). Crawl paused after 3,917 of 8,677 sitemap pages (hh slowed responses; we back off) | 816 hh posts stored, 808 unique (0 duplicates of Telegram posts); Gemini: 259 IT vacancies (54 with salary), all posted 2026-11-09…21, i.e. in the test period |
| 2026-11-22 | Label check: Gemini salary vs hh's structured salary field on the 54 hh IT posts that have both | 54/54 within 5% (median difference $0); Gemini found a salary on every post where hh has one |
| 2026-11-22 | hh.uz crawl run 3: discovery from 596 IT category pages (`/vacancies/<title>`, first page only) instead of the full sitemap | 1,007 new pages checked (54% IT vs ~10% from the sitemap), +545 posts; hh total 1,361 posts → 559 unique IT vacancies (115 with salary), posted 2026-10-23…11-22 (all in the test period). All unique IT vacancies: 4,238 |
| 2026-11-22 | Label check repeated on all hh IT posts: Gemini salary vs hh's structured salary field | 114/114 within 5%; 1 post where Gemini found a salary that hh's field lacks |
| 2026-11-22 | hh.uz runs 4–5: hh search over 21 IT roles (all pages, active only: hh ignores `archived`/date filters when logged out); 403 on restricted vacancies no longer treated as a block; wider IT title filter (+33 re-checked); Wayback Machine ids for past vacancies (288 pages) | hh 1,570 posts → 696 unique IT vacancies (158 with salary); only 18 hh IT posts are older than TEST_START. All unique IT vacancies: 4,375 (train 3,421 / test 954) |
