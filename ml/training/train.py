"""Train 3 models: temperature regression, rain binary, condition classification.

Run inside the project root with DATABASE_URL set (e.g. via .env):
    python -m ml.training.train
"""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier, CatBoostRegressor
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.features import (  # noqa: E402
    CONDITION_CLASSES,
    build_training_frame,
    feature_columns,
)

ARTIFACTS = ROOT / "ml" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger("train")

HORIZON = 6  # hours ahead


def load_data(database_url: str) -> pd.DataFrame:
    engine = create_engine(database_url)
    q = """
        SELECT o.city_id, o.ts, o.temperature_c, o.humidity, o.pressure_hpa,
               o.wind_speed, o.wind_direction, o.cloud_cover, o.precipitation_mm,
               o.weather_code, o.weather_main
        FROM weather_observations o
        WHERE o.source IN ('open_meteo_archive', 'open_meteo')
        ORDER BY o.city_id, o.ts
    """
    df = pd.read_sql(q, engine)
    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    return df


def naive_baseline_temp(df: pd.DataFrame) -> float:
    """Naive: predict T(t+H) = T(t). Returns MAE."""
    sub = df.dropna(subset=["temperature_c", "target_temp"])
    return mean_absolute_error(sub["target_temp"], sub["temperature_c"])


def naive_baseline_rain(df: pd.DataFrame) -> float:
    """Naive: predict majority class."""
    sub = df.dropna(subset=["target_rain"])
    majority = int(sub["target_rain"].mean() >= 0.5)
    pred = np.full(len(sub), majority)
    return accuracy_score(sub["target_rain"], pred)


def naive_baseline_condition(df: pd.DataFrame) -> float:
    sub = df.dropna(subset=["target_condition", "weather_main"])
    return accuracy_score(sub["target_condition"], sub["weather_main"])


def train_temperature(df: pd.DataFrame, features: list[str]) -> tuple[CatBoostRegressor, dict]:
    sub = df.dropna(subset=features + ["target_temp"]).copy()
    X = sub[features]
    y = sub["target_temp"]

    tscv = TimeSeriesSplit(n_splits=4)
    mae_scores, rmse_scores = [], []
    for tr, va in tscv.split(X):
        model = CatBoostRegressor(
            iterations=400, learning_rate=0.05, depth=6, loss_function="MAE",
            verbose=False, random_seed=42,
        )
        model.fit(X.iloc[tr], y.iloc[tr])
        pred = model.predict(X.iloc[va])
        mae_scores.append(mean_absolute_error(y.iloc[va], pred))
        rmse_scores.append(np.sqrt(mean_squared_error(y.iloc[va], pred)))

    final = CatBoostRegressor(
        iterations=600, learning_rate=0.05, depth=6, loss_function="MAE",
        verbose=False, random_seed=42,
    )
    final.fit(X, y)
    metrics = {
        "cv_mae_mean": float(np.mean(mae_scores)),
        "cv_mae_std": float(np.std(mae_scores)),
        "cv_rmse_mean": float(np.mean(rmse_scores)),
        "naive_mae": float(naive_baseline_temp(sub)),
        "n_samples": int(len(sub)),
        "horizon_hours": HORIZON,
    }
    return final, metrics


def train_rain(df: pd.DataFrame, features: list[str]) -> tuple[CatBoostClassifier, dict]:
    sub = df.dropna(subset=features + ["target_rain"]).copy()
    X = sub[features]
    y = sub["target_rain"].astype(int)

    tscv = TimeSeriesSplit(n_splits=4)
    acc_scores, f1_scores = [], []
    for tr, va in tscv.split(X):
        model = CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6, verbose=False,
            random_seed=42, auto_class_weights="Balanced",
        )
        model.fit(X.iloc[tr], y.iloc[tr])
        pred = model.predict(X.iloc[va])
        acc_scores.append(accuracy_score(y.iloc[va], pred))
        f1_scores.append(f1_score(y.iloc[va], pred, zero_division=0))

    final = CatBoostClassifier(
        iterations=500, learning_rate=0.05, depth=6, verbose=False,
        random_seed=42, auto_class_weights="Balanced",
    )
    final.fit(X, y)
    metrics = {
        "cv_accuracy_mean": float(np.mean(acc_scores)),
        "cv_f1_mean": float(np.mean(f1_scores)),
        "naive_accuracy": float(naive_baseline_rain(sub)),
        "positive_rate": float(y.mean()),
        "n_samples": int(len(sub)),
        "horizon_hours": HORIZON,
    }
    return final, metrics


def train_condition(df: pd.DataFrame, features: list[str]) -> tuple[CatBoostClassifier, dict]:
    sub = df.dropna(subset=features + ["target_condition"]).copy()
    sub = sub[sub["target_condition"].isin(CONDITION_CLASSES)].copy()
    X = sub[features]
    y = sub["target_condition"]

    tscv = TimeSeriesSplit(n_splits=4)
    acc_scores, f1_scores = [], []
    for tr, va in tscv.split(X):
        model = CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6, verbose=False,
            random_seed=42, loss_function="MultiClass",
        )
        model.fit(X.iloc[tr], y.iloc[tr])
        pred = model.predict(X.iloc[va]).flatten()
        acc_scores.append(accuracy_score(y.iloc[va], pred))
        f1_scores.append(f1_score(y.iloc[va], pred, average="macro", zero_division=0))

    final = CatBoostClassifier(
        iterations=500, learning_rate=0.05, depth=6, verbose=False,
        random_seed=42, loss_function="MultiClass",
    )
    final.fit(X, y)
    metrics = {
        "cv_accuracy_mean": float(np.mean(acc_scores)),
        "cv_macro_f1_mean": float(np.mean(f1_scores)),
        "naive_accuracy": float(naive_baseline_condition(sub)),
        "classes": sorted(y.unique().tolist()),
        "n_samples": int(len(sub)),
        "horizon_hours": HORIZON,
    }
    return final, metrics


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    log.info("loading data")
    df = load_data(database_url)
    log.info("rows: %d, cities: %d", len(df), df["city_id"].nunique())
    if df.empty:
        raise SystemExit("no data — run ingestor first")

    df = build_training_frame(df, horizon_hours=HORIZON)
    features = feature_columns()

    log.info("training temperature regressor")
    temp_model, temp_metrics = train_temperature(df, features)
    log.info("temp metrics: %s", temp_metrics)

    log.info("training rain classifier")
    rain_model, rain_metrics = train_rain(df, features)
    log.info("rain metrics: %s", rain_metrics)

    log.info("training condition classifier")
    cond_model, cond_metrics = train_condition(df, features)
    log.info("condition metrics: %s", cond_metrics)

    joblib.dump({"model": temp_model, "features": features}, ARTIFACTS / "temp_model.joblib")
    joblib.dump({"model": rain_model, "features": features}, ARTIFACTS / "rain_model.joblib")
    joblib.dump({"model": cond_model, "features": features}, ARTIFACTS / "condition_model.joblib")

    metrics_all = {
        "temperature": temp_metrics,
        "rain": rain_metrics,
        "condition": cond_metrics,
        "feature_columns": features,
    }
    (ARTIFACTS / "metrics.json").write_text(json.dumps(metrics_all, indent=2))
    log.info("artifacts saved to %s", ARTIFACTS)


if __name__ == "__main__":
    main()
