"""Feature engineering shared between training and inference.

Kept dependency-free of the ORM so we can import from the API service too.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NUM_BASE_FEATURES = [
    "temperature_c",
    "humidity",
    "pressure_hpa",
    "wind_speed",
    "wind_direction",
    "cloud_cover",
    "precipitation_mm",
]

CONDITION_CLASSES = ["Clear", "Clouds", "Rain", "Snow", "Fog", "Thunderstorm"]


def add_time_features(df: pd.DataFrame, ts_col: str = "ts") -> pd.DataFrame:
    df = df.copy()
    ts = pd.to_datetime(df[ts_col], utc=True)
    df["hour"] = ts.dt.hour
    df["dayofyear"] = ts.dt.dayofyear
    df["month"] = ts.dt.month
    df["dayofweek"] = ts.dt.dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["doy_sin"] = np.sin(2 * np.pi * df["dayofyear"] / 365.25)
    df["doy_cos"] = np.cos(2 * np.pi * df["dayofyear"] / 365.25)
    # Wind direction is cyclic (0° ≈ 360°), so encode as sin/cos like hours/days.
    if "wind_direction" in df.columns:
        rad = 2 * np.pi * df["wind_direction"].fillna(0) / 360
        df["wind_dir_sin"] = np.sin(rad)
        df["wind_dir_cos"] = np.cos(rad)
    return df


def add_lag_features(
    df: pd.DataFrame,
    group_col: str = "city_id",
    ts_col: str = "ts",
    target_col: str = "temperature_c",
    lags=(1, 3, 6, 12, 24),
    windows=(3, 12, 24),
) -> pd.DataFrame:
    df = df.sort_values([group_col, ts_col]).copy()
    g = df.groupby(group_col, group_keys=False)[target_col]
    for L in lags:
        df[f"t_lag_{L}"] = g.shift(L)
    for W in windows:
        df[f"t_roll_mean_{W}"] = df.groupby(group_col)[target_col].transform(
            lambda x: x.shift(1).rolling(W, min_periods=1).mean()
        )
        df[f"t_roll_std_{W}"] = df.groupby(group_col)[target_col].transform(
            lambda x: x.shift(1).rolling(W, min_periods=1).std()
        )
    return df


def feature_columns() -> list[str]:
    # wind_direction is replaced by wind_dir_sin / wind_dir_cos (cyclical encoding)
    base = [c for c in NUM_BASE_FEATURES if c not in ("temperature_c", "wind_direction")]
    time_feats = ["hour", "dayofyear", "month", "dayofweek",
                  "hour_sin", "hour_cos", "doy_sin", "doy_cos",
                  "wind_dir_sin", "wind_dir_cos"]
    lag_feats = [f"t_lag_{L}" for L in (1, 3, 6, 12, 24)]
    roll_feats = []
    for W in (3, 12, 24):
        roll_feats.append(f"t_roll_mean_{W}")
        roll_feats.append(f"t_roll_std_{W}")
    return base + time_feats + lag_feats + roll_feats + ["city_id"]


FEATURE_DESCRIPTIONS = {
    "humidity": "Относительная влажность, %",
    "pressure_hpa": "Атмосферное давление, hPa",
    "wind_speed": "Скорость ветра, м/с",
    "wind_direction": "Направление ветра, градусы (сырое значение)",
    "wind_dir_sin": "Направление ветра (синус, циклическое кодирование)",
    "wind_dir_cos": "Направление ветра (косинус, циклическое кодирование)",
    "cloud_cover": "Облачность, %",
    "precipitation_mm": "Осадки за час, мм",
    "hour": "Час суток (UTC)",
    "dayofyear": "Номер дня в году",
    "month": "Месяц",
    "dayofweek": "День недели",
    "hour_sin": "Час суток (синус, циклическое кодирование)",
    "hour_cos": "Час суток (косинус, циклическое кодирование)",
    "doy_sin": "День года (синус, сезонность)",
    "doy_cos": "День года (косинус, сезонность)",
    "t_lag_1": "Температура 1 час назад",
    "t_lag_3": "Температура 3 часа назад",
    "t_lag_6": "Температура 6 часов назад",
    "t_lag_12": "Температура 12 часов назад",
    "t_lag_24": "Температура сутки назад",
    "t_roll_mean_3": "Средняя температура за 3 часа",
    "t_roll_mean_12": "Средняя температура за 12 часов",
    "t_roll_mean_24": "Средняя температура за сутки",
    "t_roll_std_3": "Стандартное отклонение T за 3 часа",
    "t_roll_std_12": "Стандартное отклонение T за 12 часов",
    "t_roll_std_24": "Стандартное отклонение T за сутки",
    "city_id": "Идентификатор города",
}


def build_training_frame(df: pd.DataFrame, horizon_hours: int = 6) -> pd.DataFrame:
    """Add features and create target columns shifted into the future."""
    df = add_time_features(df)
    df = add_lag_features(df)
    df = df.sort_values(["city_id", "ts"]).copy()
    df["target_temp"] = df.groupby("city_id")["temperature_c"].shift(-horizon_hours)
    df["target_rain"] = (
        df.groupby("city_id")["precipitation_mm"].shift(-horizon_hours).fillna(0) > 0.1
    ).astype(int)
    df["target_condition"] = df.groupby("city_id")["weather_main"].shift(-horizon_hours)
    return df
