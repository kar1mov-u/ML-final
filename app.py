"""Web app: paste a vacancy -> estimated level and salary.

    python app.py                       # http://127.0.0.1:8000
    HOST=0.0.0.0 PORT=8000 python app.py   # on the server

Routes
    GET  /             the page with the form
    GET  /dashboard    weekly market view: postings per week, top skills, salary by level
    GET  /monitor      monitoring: predictions per day, live metric per new week, odd inputs
    POST /             form submit -> result on the page
    POST /feedback     the user corrects a prediction -> stored as its label
    POST /api/predict  JSON {"text": "..."} -> JSON result (for testing / other clients)
    GET  /health       "ok" + model version (for uptime checks)
Every successful prediction is written to the prediction_log table.
"""
import os

from flask import Flask, jsonify, render_template, request

from jobtracker.dashboard import market_stats
from jobtracker.db import connect
from jobtracker.monitoring import live_metric, usage
from jobtracker.predict import Predictor, check_feedback, check_input, log_prediction, save_feedback
from jobtracker.registry import live_version, released

app = Flask(__name__)
_predictor = Predictor()         # loaded at start-up


def get_predictor():
    """The model to serve. If models/LIVE now names another version (the weekly retrain promoted
    a model, or someone rolled back), load it, so no restart is needed. If loading fails, keep
    serving the current model and log why."""
    global _predictor
    wanted = live_version()
    if wanted != _predictor.version:
        try:
            _predictor = Predictor(wanted)
            app.logger.warning("now serving model %s", wanted)
        except Exception as exc:                      # broken/missing file: never take the app down
            app.logger.error("could not load model %s, still serving %s: %s",
                             wanted, _predictor.version, exc)
    return _predictor


def answer(text):
    """Shared by the page and the API: check input, predict, log. Returns a dict."""
    error, warning = check_input(text)
    if error:
        return {"error": error}
    result = get_predictor().predict(text)
    conn = connect()
    prediction_id = log_prediction(conn, text, result)
    conn.close()
    return {**result, "warning": warning, "id": prediction_id}


@app.route("/", methods=["GET", "POST"])
def index():
    text = request.form.get("text", "") if request.method == "POST" else ""
    result = answer(text) if request.method == "POST" else None
    return render_template("index.html", text=text, result=result, version=get_predictor().version)


@app.post("/feedback")
def feedback():
    error, label = check_feedback(request.form.get("level"), request.form.get("salary_usd"))
    saved = False
    if not error:
        conn = connect()
        saved = save_feedback(conn, request.form.get("id", type=int), label)
        conn.close()
        error = None if saved else "That prediction was not found."
    message = error or "Thank you! Your correction was saved and will help the next model."
    return render_template("index.html", text="", result=None, version=get_predictor().version,
                           message=message)


@app.get("/dashboard")
def dashboard():
    conn = connect()
    stats = market_stats(conn)
    conn.close()
    return render_template("dashboard.html", s=stats)


@app.get("/monitor")
def monitor():
    predictor = get_predictor()
    meta = predictor.meta
    offline = {
        "level_f1": meta["cv"]["level"][meta["level_model"]]["macro_f1"],
        "salary_mae": meta["cv"]["salary"][meta["salary_model"]]["mae"],
    }
    conn = connect()
    # before the release, new weeks belong to the frozen test set: no live metric yet
    live = live_metric(conn, predictor, meta["created"]) if released() else None
    page = render_template("monitor.html", meta=meta, offline=offline, usage=usage(conn),
                           live=live)
    conn.close()
    return page


@app.post("/api/predict")
def api_predict():
    data = request.get_json(silent=True) or {}
    result = answer(data.get("text"))
    return jsonify(result), (400 if "error" in result else 200)


@app.get("/health")
def health():
    return {"status": "ok", "model_version": get_predictor().version}


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "8000")))
