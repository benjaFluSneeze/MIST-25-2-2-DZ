"""Scrape tomorrow's forecast from Gismeteo for comparison with our model.

Uses requests + BeautifulSoup as required by the project stack.

The page exposes 8 three-hour slots inside `widget-row-*` blocks driven by the
`data-row` attribute:
  - `temperature-air`: <temperature-value value="N"> in 8 slots
  - `precipitation-bars`: .row-item .item-unit (Russian decimal comma)
  - `icon-tooltip`: .row-item[data-tooltip] with a Russian condition phrase

`fetch_tomorrow` / `parse_page` return a LIST of 8 forecast dicts (one per
3-hour slot from 00:00 to 21:00 UTC of tomorrow), so the dashboard can draw
the Gismeteo curve next to ours.
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


def fetch_tomorrow(slug: str) -> list[dict] | None:
    """Return tomorrow's per-slot forecast list, or None on failure."""
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


def parse_page(html: str) -> list[dict] | None:
    """Parse Gismeteo HTML and return list of 8 per-slot forecasts.

    Returns None if no temperature values found. Otherwise returns up to 8
    dicts with `fetched_at`, `target_ts`, `temperature_c`, `precipitation_mm`,
    `weather_main`.
    """
    soup = BeautifulSoup(html, "lxml")
    temps = _extract_temps(soup)
    if not temps:
        return None

    precips = _extract_precipitations_per_slot(soup)
    conditions = _extract_conditions_per_slot(soup)

    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    tomorrow_start = datetime.combine(
        tomorrow, datetime.min.time(), tzinfo=timezone.utc
    )
    now = datetime.now(timezone.utc)

    forecasts: list[dict] = []
    for i, temp in enumerate(temps[:8]):
        target_ts = tomorrow_start + timedelta(hours=i * 3)
        forecasts.append({
            "fetched_at": now,
            "target_ts": target_ts,
            "temperature_c": float(temp),
            "precipitation_mm": float(precips[i]) if i < len(precips) else 0.0,
            "weather_main": conditions[i] if i < len(conditions) else None,
        })
    return forecasts


def _extract_temps(soup: BeautifulSoup) -> list[float]:
    """Pull tomorrow's per-slot temperatures from <temperature-value value=...>."""
    out: list[float] = []
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


def _extract_precipitations_per_slot(soup: BeautifulSoup) -> list[float]:
    """Per-slot precipitation values in mm (one per 3-hour slot)."""
    out: list[float] = []
    row = soup.select_one('[data-row="precipitation-bars"]')
    if row is None:
        return out
    for row_item in row.select(".row-item"):
        unit = row_item.select_one(".item-unit")
        if unit is None:
            out.append(0.0)
            continue
        text = unit.get_text(strip=True).replace(",", ".")
        m = _NUMBER_RE.search(text)
        if not m:
            out.append(0.0)
            continue
        try:
            v = float(m.group(0))
        except ValueError:
            out.append(0.0)
            continue
        out.append(v if 0 <= v <= 200 else 0.0)
    return out


_CONDITION_KEYWORDS = (
    ("гроз", "Thunderstorm"),
    ("снег", "Snow"),
    ("дожд", "Rain"),
    ("туман", "Fog"),
    ("пасмур", "Clouds"),
    ("облач", "Clouds"),
    ("ясно", "Clear"),
)


def _classify_tooltip(tip: str) -> str | None:
    tip = (tip or "").lower()
    for kw, label in _CONDITION_KEYWORDS:
        if kw in tip:
            return label
    return None


def _extract_conditions_per_slot(soup: BeautifulSoup) -> list[str | None]:
    """Per-slot weather class derived from each `data-tooltip` phrase."""
    out: list[str | None] = []
    row = soup.select_one('[data-row="icon-tooltip"]')
    if row is None:
        return out
    for el in row.select(".row-item[data-tooltip]"):
        out.append(_classify_tooltip(el.get("data-tooltip", "")))
    return out
