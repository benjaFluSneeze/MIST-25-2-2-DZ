"""Loads trained models from disk and runs inference."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from ml.features import add_lag_features, add_time_features

from .models import WeatherObservation

log = logging.getLogger(__name__)

ARTIFACT_DIR = Path("/app/ml/artifacts")


class ModelBundle:
    def __init__(self):
        self.temp = self._load("temp_model.joblib")
        self.rain = self._load("rain_model.joblib")
        self.condition = self._load("condition_model.joblib")
        self.metrics = self._load_metrics()

    def _load(self, name: str):
        path = ARTIFACT_DIR / name
        if not path.exists():
            log.warning("model artifact %s not found", path)
            return None
        try:
            return joblib.load(path)
        except Exception as e:  # noqa: BLE001
            log.exception("failed to load %s: %s", path, e)
            return None

    def _load_metrics(self) -> dict:
        path = ARTIFACT_DIR / "metrics.json"
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:  # noqa: BLE001
            return {}

    @property
    def status(self) -> dict[str, bool]:
        return {
            "temperature": self.temp is not None,
            "rain": self.rain is not None,
            "condition": self.condition is not None,
        }


_bundle: ModelBundle | None = None


def get_bundle() -> ModelBundle:
    global _bundle
    if _bundle is None:
        _bundle = ModelBundle()
    return _bundle


def reload_bundle() -> None:
    global _bundle
    _bundle = None
    get_bundle()


def _load_recent_frame(session: Session, city_id: int, lookback_hours: int = 48) -> pd.DataFrame:
    rows = session.execute(
        select(WeatherObservation)
        .where(WeatherObservation.city_id == city_id)
        .where(WeatherObservation.source.in_(["open_meteo", "open_meteo_archive"]))
        .order_by(WeatherObservation.ts.desc())
        .limit(lookback_hours)
    ).scalars().all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([
        {
            "city_id": r.city_id,
            "ts": r.ts,
            "temperature_c": r.temperature_c,
            "humidity": r.humidity,
            "pressure_hpa": r.pressure_hpa,
            "wind_speed": r.wind_speed,
            "wind_direction": r.wind_direction,
            "cloud_cover": r.cloud_cover,
            "precipitation_mm": r.precipitation_mm,
            "weather_main": r.weather_main,
        }
        for r in rows
    ])
    return df.sort_values("ts").reset_index(drop=True)


def _run_inference(last_row: pd.DataFrame) -> dict:
    """Run all 3 models on a single prepared row. Used by both predict modes."""
    bundle = get_bundle()
    feats = None
    for b in (bundle.temp, bundle.rain, bundle.condition):
        if b is not None:
            feats = b["features"]
            break
    if feats is None:
        raise RuntimeError("no models loaded")

    for c in feats:
        if c not in last_row.columns:
            last_row[c] = 0
    X = last_row[feats].fillna(0)

    out = {"based_on_ts": last_row["ts"].iloc[0].to_pydatetime()}

    if bundle.temp is not None:
        out["predicted_temperature_c"] = float(bundle.temp["model"].predict(X)[0])
    else:
        out["predicted_temperature_c"] = None

    if bundle.rain is not None:
        proba = bundle.rain["model"].predict_proba(X)[0]
        classes = bundle.rain["model"].classes_.tolist()
        idx_pos = classes.index(1) if 1 in classes else (classes.index("1") if "1" in classes else None)
        p = float(proba[idx_pos]) if idx_pos is not None else float(proba[-1])
        out["predicted_rain_probability"] = p
        out["predicted_rain"] = p >= 0.5
    else:
        out["predicted_rain_probability"] = None
        out["predicted_rain"] = None

    if bundle.condition is not None:
        pred = bundle.condition["model"].predict(X)
        cls = pred[0]
        if hasattr(cls, "__iter__") and not isinstance(cls, str):
            cls = cls[0]
        out["predicted_condition"] = str(cls)
    else:
        out["predicted_condition"] = None

    return out


def predict_for_city(session: Session, city_id: int) -> dict:
    """Predict using the latest DB observation as input."""
    df = _load_recent_frame(session, city_id)
    if df.empty:
        raise ValueError("no recent observations for this city")
    df = add_time_features(df)
    df = add_lag_features(df)
    return _run_inference(df.iloc[-1:].copy())


def predict_with_overrides(
    session: Session, city_id: int, overrides: dict
) -> dict:
    """Predict treating `overrides` as a synthetic 'current' observation.

    Pulls real DB history for the city to compute lag/rolling features,
    then appends a synthetic row with user-provided current conditions
    one hour after the latest DB observation, and predicts from that row.
    """
    history = _load_recent_frame(session, city_id)
    if history.empty:
        raise ValueError("no recent observations for this city")

    last_ts = pd.to_datetime(history["ts"].iloc[-1], utc=True)
    synthetic = {
        "city_id": city_id,
        "ts": last_ts + pd.Timedelta(hours=1),
        "temperature_c": overrides.get("temperature_c"),
        "humidity": overrides.get("humidity"),
        "pressure_hpa": overrides.get("pressure_hpa"),
        "wind_speed": overrides.get("wind_speed"),
        "wind_direction": overrides.get("wind_direction"),
        "cloud_cover": overrides.get("cloud_cover"),
        "precipitation_mm": overrides.get("precipitation_mm"),
        "weather_main": None,
    }
    full = pd.concat([history, pd.DataFrame([synthetic])], ignore_index=True)
    full = add_time_features(full)
    full = add_lag_features(full)
    return _run_inference(full.iloc[-1:].copy())
