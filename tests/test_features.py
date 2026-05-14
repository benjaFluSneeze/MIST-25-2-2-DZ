"""Smoke tests for feature engineering — no DB or network required."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ml.features import (  # noqa: E402
    add_lag_features,
    add_time_features,
    build_training_frame,
    feature_columns,
)


def _toy_df(n_hours=72):
    ts = pd.date_range("2024-01-01", periods=n_hours, freq="h", tz="UTC")
    return pd.DataFrame({
        "city_id": [1] * n_hours,
        "ts": ts,
        "temperature_c": np.linspace(-5, 10, n_hours),
        "humidity": np.linspace(60, 90, n_hours),
        "pressure_hpa": np.linspace(1010, 1020, n_hours),
        "wind_speed": np.linspace(1, 5, n_hours),
        "wind_direction": np.linspace(0, 360, n_hours),
        "cloud_cover": np.linspace(0, 100, n_hours),
        "precipitation_mm": [0.0] * (n_hours - 5) + [0.5] * 5,
        "weather_main": ["Clear"] * (n_hours - 5) + ["Rain"] * 5,
    })


def test_add_time_features_creates_expected_columns():
    df = add_time_features(_toy_df())
    for col in ("hour", "month", "hour_sin", "hour_cos", "doy_sin", "doy_cos"):
        assert col in df.columns
    assert df["hour_sin"].between(-1, 1).all()


def test_add_lag_features_creates_lag_columns():
    df = add_lag_features(_toy_df())
    assert "t_lag_1" in df.columns
    assert "t_roll_mean_3" in df.columns
    # first row should have NaN lag
    assert pd.isna(df.iloc[0]["t_lag_1"])


def test_build_training_frame_has_targets():
    df = build_training_frame(_toy_df(), horizon_hours=6)
    assert "target_temp" in df.columns
    assert "target_rain" in df.columns
    assert "target_condition" in df.columns
    # last 6 rows should have NaN target_temp (shifted out)
    assert df["target_temp"].tail(6).isna().all()


def test_feature_columns_non_empty():
    cols = feature_columns()
    assert len(cols) > 5
    assert "city_id" in cols
