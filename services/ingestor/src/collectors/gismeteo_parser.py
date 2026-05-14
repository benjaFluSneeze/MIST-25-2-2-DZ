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


# Strict: a sign, digits, optional decimal, followed by a degree sign in the same string.
_TEMP_WITH_DEGREE_RE = re.compile(r"(-?\d{1,3})\s*°")
_PLAIN_NUMBER_RE = re.compile(r"-?\d{1,3}(?:\.\d+)?")


def _extract_temps(soup: BeautifulSoup) -> list[float]:
    out = []
    # Only look at elements that are actually temperature-tagged.
    for el in soup.select(
        "[class*='temperature'] .value, "
        ".unit_temperature_c, "
        ".values .value"
    ):
        text = el.get_text(" ", strip=True)
        m = _TEMP_WITH_DEGREE_RE.search(text)
        if not m:
            m = _PLAIN_NUMBER_RE.fullmatch(text)
        if not m:
            continue
        try:
            val = float(m.group(1) if m.lastindex else m.group(0))
        except (ValueError, IndexError):
            continue
        # Sanity check — real surface temperature is between -80 and 60 °C.
        if -80 <= val <= 60:
            out.append(val)
    return out[:24]


def _extract_precipitation(soup: BeautifulSoup) -> float:
    total = 0.0
    for el in soup.select(".unit_precip_mm, [class*='precipitation'] .value"):
        text = el.get_text(" ", strip=True)
        m = _PLAIN_NUMBER_RE.search(text)
        if not m:
            continue
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        if 0 <= v <= 200:
            total += v
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
