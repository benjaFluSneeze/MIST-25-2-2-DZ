"""Compare temperature forecast quality across multiple horizons.

For each horizon in {1, 3, 6, 12, 24} hours:
  * builds the target column T(t+H)
  * trains a quick CatBoost via TimeSeriesSplit
  * computes naive baseline MAE (T_pred = T_now)
  * compares them

Outputs a CSV and a PNG chart to docs/, plus an INFO log table.

Run (locally or inside the api container):
    DATABASE_URL=... python -m ml.training.horizon_analysis
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy import create_engine

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ml.features import add_lag_features, add_time_features, feature_columns  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s | %(message)s")
log = logging.getLogger("horizon")

HORIZONS = [1, 3, 6, 12, 24]


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


def evaluate_horizon(df: pd.DataFrame, features: list[str], horizon: int) -> dict:
    work = df.copy()
    work["target_temp"] = work.groupby("city_id")["temperature_c"].shift(-horizon)
    sub = work.dropna(subset=features + ["target_temp"]).copy()
    if sub.empty:
        return {"horizon_h": horizon, "model_mae": float("nan"), "naive_mae": float("nan")}

    X = sub[features]
    y = sub["target_temp"]

    tscv = TimeSeriesSplit(n_splits=3)
    model_maes = []
    for tr, va in tscv.split(X):
        model = CatBoostRegressor(
            iterations=200, learning_rate=0.05, depth=6,
            loss_function="MAE", verbose=False, random_seed=42,
        )
        model.fit(X.iloc[tr], y.iloc[tr])
        pred = model.predict(X.iloc[va])
        model_maes.append(mean_absolute_error(y.iloc[va], pred))

    model_mae = float(np.mean(model_maes))
    naive_mae = float(mean_absolute_error(sub["target_temp"], sub["temperature_c"]))
    gap = naive_mae - model_mae
    gain_pct = 100.0 * gap / naive_mae if naive_mae else 0.0
    return {
        "horizon_h": horizon,
        "model_mae": model_mae,
        "naive_mae": naive_mae,
        "absolute_gain_c": gap,
        "relative_gain_pct": gain_pct,
        "n_samples": int(len(sub)),
    }


def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    log.info("loading observations")
    raw = load_data(database_url)
    log.info("rows: %d, cities: %d", len(raw), raw["city_id"].nunique())

    log.info("computing lag/time features once")
    enriched = add_time_features(raw)
    enriched = add_lag_features(enriched)
    features = feature_columns()

    rows = []
    for h in HORIZONS:
        log.info("--- horizon +%d h ---", h)
        result = evaluate_horizon(enriched, features, h)
        rows.append(result)
        log.info(
            "  model MAE=%.2f °C  |  naive MAE=%.2f °C  |  gain=%.2f °C (%.1f%%)",
            result["model_mae"], result["naive_mae"],
            result["absolute_gain_c"], result["relative_gain_pct"],
        )

    out = pd.DataFrame(rows)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    out.to_csv(docs / "horizon_analysis.csv", index=False)
    log.info("\n%s", out.to_string(index=False))

    _plot(out, docs / "horizon_analysis.png")


def _plot(out: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_facecolor("#0f0f1a")
    fig.patch.set_facecolor("#0f0f1a")

    ax.plot(out["horizon_h"], out["naive_mae"], "o--",
            label="Naive baseline\n(T(t+H) = T(t))", color="#94a3b8", linewidth=2)
    ax.plot(out["horizon_h"], out["model_mae"], "o-",
            label="CatBoost (наша модель)", color="#6366f1", linewidth=2.5)
    ax.fill_between(
        out["horizon_h"], out["model_mae"], out["naive_mae"],
        where=(out["naive_mae"] >= out["model_mae"]),
        interpolate=True, color="#6366f1", alpha=0.15, label="Выигрыш модели",
    )

    for _, row in out.iterrows():
        ax.annotate(
            f"{row['model_mae']:.2f}",
            (row["horizon_h"], row["model_mae"]),
            textcoords="offset points", xytext=(0, 12),
            ha="center", fontsize=9, color="#f1f5f9",
        )

    ax.set_xlabel("Горизонт прогноза, часов", fontsize=12, color="#f1f5f9")
    ax.set_ylabel("MAE (средняя ошибка), °C", fontsize=12, color="#f1f5f9")
    ax.set_title(
        "Качество прогноза температуры vs дальность горизонта",
        fontsize=13, pad=12, color="#f1f5f9",
    )
    ax.set_xticks(HORIZONS)
    ax.tick_params(colors="#94a3b8")
    for spine in ax.spines.values():
        spine.set_color("#2d2d4a")
    ax.grid(alpha=0.2, color="#2d2d4a")
    leg = ax.legend(loc="upper left", facecolor="#1a1a2e",
                    edgecolor="#2d2d4a", labelcolor="#f1f5f9")
    for text in leg.get_texts():
        text.set_color("#f1f5f9")

    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=fig.get_facecolor())
    log.info("chart saved to %s", path)


if __name__ == "__main__":
    main()
