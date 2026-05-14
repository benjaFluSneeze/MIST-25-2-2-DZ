"""Scrape tomorrow's forecast from Gismeteo for comparison with our model.

Uses requests + BeautifulSoup as required by the project stack.

The page exposes 3-hour slots inside `widget-row-*` blocks driven by the
`data-row` attribute:
  - `temperature-air`: <temperature-value value="N"> in 8 slots
  - `precipitation-bars`: .row-item .item-unit (Russian decimal comma)
  - `icon-tooltip`: .row-item[data-tooltip] with a Russian condition phrase
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

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def fetch_tomorrow(slug: str) -> dict | None:
    """Return tomorrow's daily summary or None if page unreachable."""
    url = BASE.format(slug=slug)
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        log.warning("gismeteo request failed for %s: %s", slug, e)
        return None
    if r.status_code != 200:
        log.warning("gismeteo %s: %s", slug, r.status_code)
        return None

    return parse_page(r.text)


def parse_page(html: str) -> dict | None:
    """Parse Gismeteo HTML and return aggregated tomorrow forecast.

    Returns None if no temperature values found.
    """
    soup = BeautifulSoup(html, "lxml")
    temps = _extract_temps(soup)
    if not temps:
        return None

    precip = _extract_precipitation(soup)
    condition = _extract_condition(soup)

    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    target_ts = datetime.combine(
        tomorrow, datetime.min.time(), tzinfo=timezone.utc
    ) + timedelta(hours=12)

    return {
        "fetched_at": datetime.now(timezone.utc),
        "target_ts": target_ts,
        "temperature_c": sum(temps) / len(temps),
        "precipitation_mm": precip,
        "weather_main": condition,
    }


def _extract_temps(soup: BeautifulSoup) -> list[float]:
    """Pull tomorrow's hourly temperatures from <temperature-value value=...>."""
    out = []
    chart = soup.select_one('[data-row="temperature-air"] .values')
    if chart is None:
        return out
    for tv in chart.select("temperature-value[value]"):
        raw = tv.get("value", "").replace(",", ".")
        try:
            v = float(raw)
        except ValueError:
            continue
        if -80 <= v <= 60:
            out.append(v)
    return out


def _extract_precipitation(soup: BeautifulSoup) -> float:
    """Sum precipitation values (mm) from the precipitation-bars row."""
    total = 0.0
    row = soup.select_one('[data-row="precipitation-bars"]')
    if row is None:
        return total
    for unit in row.select(".row-item .item-unit"):
        text = unit.get_text(strip=True).replace(",", ".")
        m = _NUMBER_RE.search(text)
        if not m:
            continue
        try:
            v = float(m.group(0))
        except ValueError:
            continue
        if 0 <= v <= 200:
            total += v
    return total


_CONDITION_KEYWORDS = (
    ("гроз", "Thunderstorm"),
    ("снег", "Snow"),
    ("дожд", "Rain"),
    ("туман", "Fog"),
    ("пасмур", "Clouds"),
    ("облач", "Clouds"),
    ("ясно", "Clear"),
)


def _extract_condition(soup: BeautifulSoup) -> str | None:
    """Pick the dominant weather class from .row-item[data-tooltip] tooltips.

    Priority is given to severe conditions (thunderstorm > snow > rain > fog
    > clouds > clear): if any 3-hour slot mentions a severe class, that
    class wins for the day. Otherwise we fall back to the most frequent.
    """
    row = soup.select_one('[data-row="icon-tooltip"]')
    if row is None:
        return None
    tooltips = [
        el.get("data-tooltip", "").lower()
        for el in row.select(".row-item[data-tooltip]")
    ]
    if not tooltips:
        return None

    counts: dict[str, int] = {}
    for tip in tooltips:
        for kw, label in _CONDITION_KEYWORDS:
            if kw in tip:
                counts[label] = counts.get(label, 0) + 1
                break

    if not counts:
        return None

    # Severe-first priority among classes that appeared at least once
    for _, label in _CONDITION_KEYWORDS[:4]:  # Thunderstorm, Snow, Rain, Fog
        if label in counts:
            return label
    # Otherwise — most frequent
    return max(counts.items(), key=lambda x: x[1])[0]
