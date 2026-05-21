"""Train temperature / rain / condition models at multiple forecast horizons.

For each horizon in HORIZONS (default 3, 6, 9, ..., 24 hours) we build the
appropriate target column, train a CatBoost model with TimeSeriesSplit CV,
and pickle the resulting ensemble.

Run inside the project root with DATABASE_URL set:
    python -m ml.training.train
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
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
    FEATURE_DESCRIPTIONS,
    add_lag_features,
    add_time_features,
    feature_columns,
)

ARTIFACTS = ROOT / "ml" / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger("train")

HORIZONS = [3, 6, 9, 12, 15, 18, 21, 24]


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


def build_targets(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Add target_temp/target_rain/target_condition shifted by `horizon` hours."""
    df = df.sort_values(["city_id", "ts"]).copy()
    df["target_temp"] = df.groupby("city_id")["temperature_c"].shift(-horizon)
    df["target_rain"] = (
        df.groupby("city_id")["precipitation_mm"].shift(-horizon).fillna(0) > 0.1
    ).astype(int)
    df["target_condition"] = df.groupby("city_id")["weather_main"].shift(-horizon)
    return df


def train_temperature(df: pd.DataFrame, features: list[str], horizon: int):
    sub = df.dropna(subset=features + ["target_temp"]).copy()
    X = sub[features]
    y = sub["target_temp"]

    tscv = TimeSeriesSplit(n_splits=4)
    mae_scores, rmse_scores = [], []
    for tr, va in tscv.split(X):
        m = CatBoostRegressor(
            iterations=400, learning_rate=0.05, depth=6, loss_function="MAE",
            verbose=False, random_seed=42,
        )
        m.fit(X.iloc[tr], y.iloc[tr])
        pred = m.predict(X.iloc[va])
        mae_scores.append(mean_absolute_error(y.iloc[va], pred))
        rmse_scores.append(np.sqrt(mean_squared_error(y.iloc[va], pred)))

    final = CatBoostRegressor(
        iterations=600, learning_rate=0.05, depth=6, loss_function="MAE",
        verbose=False, random_seed=42,
    )
    final.fit(X, y)
    naive = mean_absolute_error(sub["target_temp"], sub["temperature_c"])
    metrics = {
        "cv_mae_mean": float(np.mean(mae_scores)),
        "cv_mae_std": float(np.std(mae_scores)),
        "cv_rmse_mean": float(np.mean(rmse_scores)),
        "naive_mae": float(naive),
        "n_samples": int(len(sub)),
        "horizon_hours": horizon,
    }
    return final, metrics


def train_rain(df: pd.DataFrame, features: list[str], horizon: int):
    sub = df.dropna(subset=features + ["target_rain"]).copy()
    X = sub[features]
    y = sub["target_rain"].astype(int)

    tscv = TimeSeriesSplit(n_splits=4)
    acc_scores, f1_scores = [], []
    for tr, va in tscv.split(X):
        m = CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6, verbose=False,
            random_seed=42, auto_class_weights="Balanced",
        )
        m.fit(X.iloc[tr], y.iloc[tr])
        pred = m.predict(X.iloc[va])
        acc_scores.append(accuracy_score(y.iloc[va], pred))
        f1_scores.append(f1_score(y.iloc[va], pred, zero_division=0))

    final = CatBoostClassifier(
        iterations=500, learning_rate=0.05, depth=6, verbose=False,
        random_seed=42, auto_class_weights="Balanced",
    )
    final.fit(X, y)
    majority = int(y.mean() >= 0.5)
    naive_acc = accuracy_score(y, np.full(len(y), majority))
    metrics = {
        "cv_accuracy_mean": float(np.mean(acc_scores)),
        "cv_f1_mean": float(np.mean(f1_scores)),
        "naive_accuracy": float(naive_acc),
        "positive_rate": float(y.mean()),
        "n_samples": int(len(sub)),
        "horizon_hours": horizon,
    }
    return final, metrics


def train_condition(df: pd.DataFrame, features: list[str], horizon: int):
    sub = df.dropna(subset=features + ["target_condition"]).copy()
    sub = sub[sub["target_condition"].isin(CONDITION_CLASSES)].copy()
    X = sub[features]
    y = sub["target_condition"]

    tscv = TimeSeriesSplit(n_splits=4)
    acc_scores, f1_scores = [], []
    for tr, va in tscv.split(X):
        m = CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6, verbose=False,
            random_seed=42, loss_function="MultiClass",
        )
        m.fit(X.iloc[tr], y.iloc[tr])
        pred = m.predict(X.iloc[va]).flatten()
        acc_scores.append(accuracy_score(y.iloc[va], pred))
        f1_scores.append(f1_score(y.iloc[va], pred, average="macro", zero_division=0))

    final = CatBoostClassifier(
        iterations=500, learning_rate=0.05, depth=6, verbose=False,
        random_seed=42, loss_function="MultiClass",
    )
    final.fit(X, y)
    naive_acc = accuracy_score(
        sub["target_condition"], sub["weather_main"].fillna(sub["target_condition"]),
    )
    metrics = {
        "cv_accuracy_mean": float(np.mean(acc_scores)),
        "cv_macro_f1_mean": float(np.mean(f1_scores)),
        "naive_accuracy": float(naive_acc),
        "classes": sorted(y.unique().tolist()),
        "n_samples": int(len(sub)),
        "horizon_hours": horizon,
    }
    return final, metrics


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    log.info("loading data")
    raw = load_data(database_url)
    log.info("rows: %d, cities: %d", len(raw), raw["city_id"].nunique())
    if raw.empty:
        raise SystemExit("no data — run ingestor first")

    log.info("computing lag/time features once")
    enriched = add_time_features(raw)
    enriched = add_lag_features(enriched)
    features = feature_columns()

    temp_models: dict[int, CatBoostRegressor] = {}
    rain_models: dict[int, CatBoostClassifier] = {}
    cond_models: dict[int, CatBoostClassifier] = {}

    temp_metrics: dict[str, dict] = {}
    rain_metrics: dict[str, dict] = {}
    cond_metrics: dict[str, dict] = {}

    for h in HORIZONS:
        log.info("=== horizon +%d h ===", h)
        df_h = build_targets(enriched, h)

        log.info("  training temperature")
        m_t, met_t = train_temperature(df_h, features, h)
        temp_models[h] = m_t
        temp_metrics[str(h)] = met_t
        log.info("    CV-MAE %.2f °C  vs naive %.2f °C", met_t["cv_mae_mean"], met_t["naive_mae"])

        log.info("  training rain")
        m_r, met_r = train_rain(df_h, features, h)
        rain_models[h] = m_r
        rain_metrics[str(h)] = met_r
        log.info("    CV-Acc %.1f%%  F1 %.2f  (naive %.1f%%)",
                 met_r["cv_accuracy_mean"] * 100, met_r["cv_f1_mean"],
                 met_r["naive_accuracy"] * 100)

        log.info("  training condition")
        m_c, met_c = train_condition(df_h, features, h)
        cond_models[h] = m_c
        cond_metrics[str(h)] = met_c
        log.info("    CV-Acc %.1f%%  macro-F1 %.2f  (naive %.1f%%)",
                 met_c["cv_accuracy_mean"] * 100, met_c["cv_macro_f1_mean"],
                 met_c["naive_accuracy"] * 100)

    joblib.dump(
        {"models": temp_models, "features": features, "horizons": HORIZONS},
        ARTIFACTS / "temp_models.joblib",
    )
    joblib.dump(
        {"models": rain_models, "features": features, "horizons": HORIZONS},
        ARTIFACTS / "rain_models.joblib",
    )
    joblib.dump(
        {"models": cond_models, "features": features, "horizons": HORIZONS},
        ARTIFACTS / "condition_models.joblib",
    )

    trained_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    model_version = trained_at.replace(":", "").replace("-", "").replace("+0000", "Z")
    metrics_all = {
        "model_version": model_version,
        "trained_at": trained_at,
        "horizons": HORIZONS,
        "temperature": {"horizons": temp_metrics},
        "rain": {"horizons": rain_metrics},
        "condition": {"horizons": cond_metrics},
        "feature_columns": features,
        "feature_descriptions": {f: FEATURE_DESCRIPTIONS.get(f, f) for f in features},
    }
    (ARTIFACTS / "metrics.json").write_text(
        json.dumps(metrics_all, indent=2, ensure_ascii=False)
    )
    log.info("artifacts saved to %s (model_version=%s)", ARTIFACTS, model_version)


if __name__ == "__main__":
    main()
