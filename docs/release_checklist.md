# Release checklist (first day of week 13)

- [ ] `python train.py --version v1 --final` rebuilds the model from the database and saves `models/model_v1.joblib` and `models/model_v1.json`
- [ ] The test-set score is computed once and written into `model_v1.json` (`"test"` field)
- [ ] The app loads the model file and shows its version (page footer and `/health`)
- [ ] Every prediction is logged (`prediction_log`: time, input, prediction, confidence, model_version, label, label_time)
- [ ] Bad inputs get a clear message, not a crash (empty, wrong type, too short, too long)
- [ ] Users are told what the service logs and why (note on the page)
- [ ] `git tag v1` is pushed; the service is live and works from a phone
- [ ] The experiment log is up to date
