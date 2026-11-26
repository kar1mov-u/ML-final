"""Railway pieces: the weekly timer and copying git models onto the volume."""
from datetime import datetime

from jobtracker import registry
from jobtracker.config import TASHKENT
from jobtracker.scheduler import due


def test_weekly_job_runs_once_on_monday_morning():
    monday_7am = datetime(2026, 11, 30, 7, 0, tzinfo=TASHKENT)
    assert due(monday_7am, "")[0]                                  # never ran -> run
    assert not due(monday_7am, monday_7am.strftime("%G-W%V"))[0]   # already ran this week
    assert not due(datetime(2026, 11, 30, 5, 0, tzinfo=TASHKENT), "")[0]   # too early
    assert not due(datetime(2026, 12, 1, 7, 0, tzinfo=TASHKENT), "")[0]    # Tuesday


def test_sync_copies_new_models_and_newer_live(tmp_path, monkeypatch):
    repo, volume = tmp_path / "repo", tmp_path / "volume"
    repo.mkdir()
    for name in ["model_v0.json", "model_v1.json"]:
        (repo / name).write_text("{}")
    (repo / "LIVE").write_text("v1\n")
    volume.mkdir()
    (volume / "model_v0.json").write_text('{"on": "volume"}')       # must not be overwritten
    (volume / "LIVE").write_text("v0\n")
    monkeypatch.setattr(registry, "REPO_MODELS_DIR", repo)
    monkeypatch.setattr(registry, "MODELS_DIR", volume)
    monkeypatch.setattr(registry, "LIVE_FILE", volume / "LIVE")

    registry.sync_from_repo()
    assert (volume / "model_v1.json").exists()                     # new release copied
    assert (volume / "model_v0.json").read_text() == '{"on": "volume"}'
    assert (volume / "LIVE").read_text().strip() == "v1"           # newer git release wins

    (volume / "LIVE").write_text("v2\n")                           # promoted on the server
    registry.sync_from_repo()
    assert (volume / "LIVE").read_text().strip() == "v2"           # stays
