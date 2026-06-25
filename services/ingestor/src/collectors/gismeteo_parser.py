"""Scrape Gismeteo's 3-hour-grid forecast for today and tomorrow.

Uses requests + BeautifulSoup as required by the project stack.

Each page exposes per-slot data inside `widget-row-*` blocks driven by the
`data-row` attribute. Crucially, the time-strip widget
(`.widget-row-datetime-time`) carries an explicit UTC timestamp for every
slot, so we don't have to guess local time / DST / what the city's tz is —
we just read what Gismeteo says the target UTC is.

`fetch_today` parses the base `/weather-<slug>/` page (filters past slots);
`fetch_tomorrow` parses `/weather-<slug>/tomorrow/`. Both return a list of
forecast dicts the dashboard can draw next to our model's prediction.
"""
from datetime import datetime, timezone
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


def fetch_today(slug: str, tz: str | None = None) -> list[dict] | None:
    """Today's per-slot forecast (only future slots are kept).

    `tz` is accepted but unused — Gismeteo embeds the absolute UTC of every
    slot in the page itself, so no timezone arithmetic is needed.
    """
    html = _http_get(TODAY_URL.format(slug=slug), slug)
    if html is None:
        return None
    return parse_page(html, drop_past=True)


def fetch_tomorrow(slug: str, tz: str | None = None) -> list[dict] | None:
    """Tomorrow's per-slot forecast (all 8 slots are in the future)."""
    html = _http_get(TOMORROW_URL.format(slug=slug), slug)
    if html is None:
        return None
    return parse_page(html, drop_past=False)


def parse_page(html: str, drop_past: bool = False, **_legacy) -> list[dict] | None:
    """Parse Gismeteo HTML and return list of per-slot forecasts.

    Uses the absolute UTC timestamps Gismeteo encodes in the page; no
    timezone conversion needed. `drop_past` skips slots that have already
    passed — useful for today's grid.

    Returns None if no slots found.
    """
    soup = BeautifulSoup(html, "lxml")
    slots = _extract_slots(soup)
    if not slots:
        return None

    now = datetime.now(timezone.utc)
    forecasts: list[dict] = []
    for slot in slots:
        if drop_past and slot["target_ts"] <= now:
            continue
        forecasts.append({
            "fetched_at": now,
            **slot,
        })
    return forecasts


def _extract_slots(soup: BeautifulSoup) -> list[dict]:
    """Pair UTC timestamps with the temperature, precipitation and condition
    values for each 3-hour slot of the first (current-day) widget on the page.
    """
    timestamps = _extract_slot_timestamps(soup)
    if not timestamps:
        return []
    temps = _extract_temps(soup)
    precips = _extract_precipitations_per_slot(soup)
    conditions = _extract_conditions_per_slot(soup)

    out: list[dict] = []
    n = min(len(timestamps), len(temps))
    for i in range(n):
        out.append({
            "target_ts": timestamps[i],
            "temperature_c": float(temps[i]),
            "precipitation_mm": float(precips[i]) if i < len(precips) else 0.0,
            "weather_main": conditions[i] if i < len(conditions) else None,
        })
    return out


def _extract_slot_timestamps(soup: BeautifulSoup) -> list[datetime]:
    """Read the absolute UTC of each slot from `.widget-row-datetime-time`."""
    out: list[datetime] = []
    time_row = soup.select_one(".widget-row-datetime-time")
    if time_row is None:
        return out
    for item in time_row.select(".row-item"):
        # The "now" indicator is a top-level time-value without a wrapping
        # `.row-item` with a `title` attribute. Real slots have both.
        tv = item.find("time-value", attrs={"timestamp": True})
        title = item.get("title")
        if tv is None or not title:
            continue
        try:
            ts_unix = int(tv["timestamp"])
        except (ValueError, TypeError):
            continue
        out.append(datetime.fromtimestamp(ts_unix, tz=timezone.utc))
    return out


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
