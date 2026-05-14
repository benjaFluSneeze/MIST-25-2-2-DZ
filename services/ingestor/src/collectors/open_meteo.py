from datetime import datetime, timedelta, timezone
import logging
import requests

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "cloud_cover",
    "precipitation",
    "weather_code",
]

log = logging.getLogger(__name__)


def _weather_code_to_main(code: int | None) -> str | None:
    if code is None:
        return None
    if code == 0:
        return "Clear"
    if code in (1, 2, 3):
        return "Clouds"
    if code in (45, 48):
        return "Fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "Rain"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "Snow"
    if code >= 95:
        return "Thunderstorm"
    return "Unknown"


def fetch_history(lat: float, lon: float, start_date: str, end_date: str, tz: str) -> list[dict]:
    """Return list of hourly observation dicts for the given date range."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": tz,
    }
    r = requests.get(ARCHIVE_URL, params=params, timeout=60)
    r.raise_for_status()
    payload = r.json()
    return _parse_hourly(payload)


def fetch_recent(lat: float, lon: float, tz: str, past_days: int = 2) -> list[dict]:
    """Fetch recent hourly observations (forecast API also returns past_days of history)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": ",".join(HOURLY_VARS),
        "timezone": tz,
        "past_days": past_days,
        "forecast_days": 1,
    }
    r = requests.get(FORECAST_URL, params=params, timeout=30)
    r.raise_for_status()
    payload = r.json()
    return _parse_hourly(payload)


def _parse_hourly(payload: dict) -> list[dict]:
    hourly = payload.get("hourly", {})
    times = hourly.get("time", [])
    out = []
    for i, t in enumerate(times):
        ts = datetime.fromisoformat(t).replace(tzinfo=timezone.utc)
        code = _safe(hourly, "weather_code", i)
        out.append(
            {
                "ts": ts,
                "temperature_c": _safe(hourly, "temperature_2m", i),
                "humidity": _safe(hourly, "relative_humidity_2m", i),
                "pressure_hpa": _safe(hourly, "pressure_msl", i),
                "wind_speed": _safe(hourly, "wind_speed_10m", i),
                "wind_direction": _safe(hourly, "wind_direction_10m", i),
                "cloud_cover": _safe(hourly, "cloud_cover", i),
                "precipitation_mm": _safe(hourly, "precipitation", i),
                "weather_code": int(code) if code is not None else None,
                "weather_main": _weather_code_to_main(int(code) if code is not None else None),
            }
        )
    return out


def _safe(d: dict, key: str, idx: int):
    arr = d.get(key)
    if arr is None or idx >= len(arr):
        return None
    return arr[idx]


def backfill_range(years: int):
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=365 * years)
    end = today - timedelta(days=2)
    return start.isoformat(), end.isoformat()
