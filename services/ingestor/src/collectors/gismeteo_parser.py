"""Scrape Gismeteo's 3-hour-grid forecast for today and tomorrow.

Uses requests + BeautifulSoup as required by the project stack.

Each page exposes 8 three-hour slots inside `widget-row-*` blocks driven by the
`data-row` attribute:
  - `temperature-air`: <temperature-value value="N"> in 8 slots
  - `precipitation-bars`: .row-item .item-unit (Russian decimal comma)
  - `icon-tooltip`: .row-item[data-tooltip] with a Russian condition phrase

`fetch_today` parses the base `/weather-<slug>/` page (today's grid), filtering
out past slots; `fetch_tomorrow` parses `/weather-<slug>/tomorrow/`. Both return
a list of forecast dicts the dashboard can draw next to our model's prediction.
"""
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import logging
import re
import requests
from bs4 import BeautifulSoup

TODAY_URL = "https://www.gismeteo.ru/weather-{slug}/"
TOMORROW_URL = "https://www.gismeteo.ru/weather-{slug}/tomorrow/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "ru,en;q=0.9",
}

log = logging.getLogger(__name__)

_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _http_get(url: str, slug: str) -> str | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as e:
        log.warning("gismeteo request failed for %s: %s", slug, e)
        return None
    if r.status_code != 200:
        log.warning("gismeteo %s [%s]: %s", slug, url, r.status_code)
        return None
    return r.text


def fetch_today(slug: str, tz: str = "UTC") -> list[dict] | None:
    """Today's per-slot forecast (only future slots are kept).

    `tz` is the IANA timezone of the city — Gismeteo serves each city's page
    in that city's local time, so we need it to anchor the 8 three-hour slots
    correctly when converting them to UTC.
    """
    html = _http_get(TODAY_URL.format(slug=slug), slug)
    if html is None:
        return None
    local_today = datetime.now(ZoneInfo(tz)).date()
    return parse_page(html, base_date=local_today, drop_past=True, tz=tz)


def fetch_tomorrow(slug: str, tz: str = "UTC") -> list[dict] | None:
    """Tomorrow's per-slot forecast (all 8 slots are in the future)."""
    html = _http_get(TOMORROW_URL.format(slug=slug), slug)
    if html is None:
        return None
    local_tomorrow = datetime.now(ZoneInfo(tz)).date() + timedelta(days=1)
    return parse_page(html, base_date=local_tomorrow, drop_past=False, tz=tz)


def parse_page(
    html: str,
    base_date: date | None = None,
    drop_past: bool = False,
    tz: str = "UTC",
) -> list[dict] | None:
    """Parse Gismeteo HTML and return list of per-slot forecasts.

    `base_date` is the calendar day **in the city's local timezone** that the
    page describes.
    `tz` is the IANA timezone of that city (e.g. 'Asia/Vladivostok'). Slot
    times shown on the page are in city-local hours and are converted to UTC
    before being stored.
    `drop_past` removes slots whose `target_ts` is already in the past —
    useful for today's grid, where the first few slots have already happened.

    Returns None if no temperature values found.
    """
    local_tz = ZoneInfo(tz)
    if base_date is None:
        base_date = (datetime.now(local_tz).date() + timedelta(days=1))

    soup = BeautifulSoup(html, "lxml")
    temps = _extract_temps(soup)
    if not temps:
        return None

    precips = _extract_precipitations_per_slot(soup)
    conditions = _extract_conditions_per_slot(soup)

    local_day_start = datetime.combine(base_date, datetime.min.time(), tzinfo=local_tz)
    now = datetime.now(timezone.utc)

    forecasts: list[dict] = []
    for i, temp in enumerate(temps[:8]):
        # Slots are at city-local 00:00, 03:00, ..., 21:00; convert to UTC.
        target_ts = (local_day_start + timedelta(hours=i * 3)).astimezone(timezone.utc)
        if drop_past and target_ts <= now:
            continue
        forecasts.append({
            "fetched_at": now,
            "target_ts": target_ts,
            "temperature_c": float(temp),
            "precipitation_mm": float(precips[i]) if i < len(precips) else 0.0,
            "weather_main": conditions[i] if i < len(conditions) else None,
        })
    return forecasts


def _extract_temps(soup: BeautifulSoup) -> list[float]:
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
    out: list[str | None] = []
    row = soup.select_one('[data-row="icon-tooltip"]')
    if row is None:
        return out
    for el in row.select(".row-item[data-tooltip]"):
        out.append(_classify_tooltip(el.get("data-tooltip", "")))
    return out
