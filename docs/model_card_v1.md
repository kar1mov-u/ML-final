# Model card: v1

- **What it predicts, and for whom:** the level (junior / middle / senior) and the monthly salary in USD of an
  IT job posting in Uzbekistan, for students looking for jobs and the university career centre.
- **Training data:** public Telegram IT job channels (list in `jobtracker/config.py`); rows: ; date range: ;
  labels extracted by Gemini (prompt version: ), checked against 100 hand labels (agreement: ).
- **Offline results** (from `models/model_v1.json`):

| Model | Level macro F1 (CV) | Salary MAE (CV) | Test (once) |
|---|---|---|---|
| Dummy | | | |
| Smart baseline | | | |
| Released model | | | |

- **Known weaknesses (from error analysis):**
- **What the service logs and who can see it:** time, the vacancy text with contacts removed, the prediction and
  the model version, in `prediction_log`. Only the two of us can read it.
