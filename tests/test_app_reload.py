"""The app follows models/LIVE without a restart, and a bad LIVE value never takes it down."""
import app


def test_missing_model_keeps_current(monkeypatch):
    current = app.get_predictor().version
    monkeypatch.setattr(app, "live_version", lambda: "v999")      # file does not exist
    assert app.get_predictor().version == current


def test_health_shows_version():
    resp = app.app.test_client().get("/health")
    assert resp.status_code == 200 and resp.get_json()["model_version"] == app.get_predictor().version
