"""Model registry: the files in models/ and which version users get.

    models/model_vN.joblib   both pipelines: {"level": ..., "salary": ...}
    models/model_vN.json     metrics + data info (the test score only in the v1 release)
    models/LIVE              one line, e.g. "v1": the version the app serves

Versions are never overwritten. Roll back: `echo v0 > models/LIVE` (the app picks it up).
"""
import json

import joblib

from jobtracker.config import MODEL_VERSION, MODELS_DIR

LIVE_FILE = MODELS_DIR / "LIVE"


def _paths(version):
    return MODELS_DIR / f"model_{version}.joblib", MODELS_DIR / f"model_{version}.json"


def _numbers():
    return sorted(int(p.stem.split("_v")[1]) for p in MODELS_DIR.glob("model_v*.json"))


def next_version():
    numbers = _numbers()
    return f"v{numbers[-1] + 1 if numbers else 0}"


def live_version():
    """MODEL_VERSION env var > models/LIVE > the newest version."""
    if MODEL_VERSION:
        return MODEL_VERSION
    if LIVE_FILE.exists():
        return LIVE_FILE.read_text().strip()
    if not _numbers():
        raise FileNotFoundError("No model in models/. Run: python train.py")
    return f"v{_numbers()[-1]}"


def set_live(version):
    LIVE_FILE.write_text(version + "\n")


def exists(version):
    return any(p.exists() for p in _paths(version))


def released():
    """File name of the model whose metrics hold the test score (= v1 is out), else None.
    The test set may be scored only once, so this guards train.py --final and retraining."""
    for path in MODELS_DIR.glob("model_v*.json"):
        if json.loads(path.read_text()).get("test") is not None:
            return path.name
    return None


def save(version, models: dict, meta: dict):
    if exists(version):
        raise FileExistsError(f"model_{version} already exists: versions are never overwritten.")
    model_path, meta_path = _paths(version)
    MODELS_DIR.mkdir(exist_ok=True)
    joblib.dump(models, model_path)
    meta_path.write_text(json.dumps({"version": version, **meta}, indent=2, ensure_ascii=False))


def load(version):
    """(models dict, meta dict) of one version."""
    model_path, meta_path = _paths(version)
    return joblib.load(model_path), json.loads(meta_path.read_text())
