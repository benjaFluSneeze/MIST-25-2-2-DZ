from datetime import datetime, timezone
import logging
import requests

URL = "https://api.openweathermap.org/data/2.5/weather"

log = logging.getLogger(__name__)


def fetch_current(lat: float, lon: float, api_key: str) -> dict | None:
    if not api_key:
        return None
    params = {"lat": lat, "lon": lon, "appid": api_key, "units": "metric"}
    r = requests.get(URL, params=params, timeout=30)
    if r.status_code != 200:
        log.warning("openweather %s: %s", r.status_code, r.text[:200])
        return None
    p = r.json()
    main = p.get("main", {})
    wind = p.get("wind", {})
    clouds = p.get("clouds", {})
    rain = p.get("rain", {}) or {}
    snow = p.get("snow", {}) or {}
    weather = (p.get("weather") or [{}])[0]
    return {
        "ts": datetime.fromtimestamp(p["dt"], tz=timezone.utc),
        "temperature_c": main.get("temp"),
        "humidity": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_speed": wind.get("speed"),
        "wind_direction": wind.get("deg"),
        "cloud_cover": clouds.get("all"),
        "precipitation_mm": (rain.get("1h") or 0) + (snow.get("1h") or 0),
        "weather_code": weather.get("id"),
        "weather_main": weather.get("main"),
    }
