"""Scrape tomorrow's forecast from Gismeteo for comparison with our model.

Uses requests + BeautifulSoup as required by the project stack.
"""
from datetime import datetime, timedelta, timezone
import logging
import re
import requests
from bs4 import BeautifulSoup

BASE = "https://www.gismeteo.ru/weather-{slug}/tomorrow/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9",
}

log = logging.getLogger(__name__)


def fetch_tomorrow(slug: str) -> dict | None:
    """Return rough forecast for tomorrow: avg temp, total precipitation, dominant condition."""
    url = BASE.format(slug=slug)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        log.warning("gismeteo request failed for %s: %s", slug, e)
        return None
    if r.status_code != 200:
        log.warning("gismeteo %s: %s", slug, r.status_code)
        return None

    soup = BeautifulSoup(r.text, "lxml")
    temps = _extract_temps(soup)
    precip = _extract_precipitation(soup)
    condition = _extract_condition(soup)
    if not temps:
        return None

    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    target_ts = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=12)
    return {
        "fetched_at": datetime.now(timezone.utc),
        "target_ts": target_ts,
        "temperature_c": sum(temps) / len(temps),
        "precipitation_mm": precip,
        "weather_main": condition,
    }


_TEMP_RE = re.compile(r"-?\d+")


def _extract_temps(soup: BeautifulSoup) -> list[float]:
    out = []
    for el in soup.select(".value temperature-value, .temperature-value, .value .unit_temperature_c"):
        m = _TEMP_RE.search(el.get_text(strip=True))
        if m:
            try:
                out.append(float(m.group(0)))
            except ValueError:
                pass
    if not out:
        for el in soup.find_all(string=_TEMP_RE):
            m = _TEMP_RE.search(str(el))
            if m and "°" in str(el):
                try:
                    out.append(float(m.group(0)))
                except ValueError:
                    pass
    return out[:24]


def _extract_precipitation(soup: BeautifulSoup) -> float:
    total = 0.0
    for el in soup.select(".unit_precip_mm, .item .precipitation .value"):
        try:
            total += float(_TEMP_RE.search(el.get_text(strip=True)).group(0))
        except (AttributeError, ValueError):
            continue
    return total


def _extract_condition(soup: BeautifulSoup) -> str | None:
    title = soup.find("meta", attrs={"name": "description"})
    if title and title.get("content"):
        text = title["content"].lower()
        if "дожд" in text:
            return "Rain"
        if "снег" in text:
            return "Snow"
        if "ясно" in text:
            return "Clear"
        if "облач" in text or "пасмур" in text:
            return "Clouds"
        if "гроз" in text:
            return "Thunderstorm"
    return None
