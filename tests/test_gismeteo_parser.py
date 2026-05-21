"""Tests for the Gismeteo parser using realistic markup fixtures."""
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "ingestor"))

from src.collectors.gismeteo_parser import parse_page  # noqa: E402


SAMPLE_HTML = """
<html>
<head><title>GISMETEO: Погода в Москве завтра</title></head>
<body>
  <a href="/weather-moscow-4368/">Moscow</a>

  <div class="widget-row widget-row-icon is-important" data-row="icon-tooltip">
    <div class="row-item" data-tooltip="Пасмурно"></div>
    <div class="row-item" data-tooltip="Облачно"></div>
    <div class="row-item" data-tooltip="Пасмурно, небольшой дождь"></div>
    <div class="row-item" data-tooltip="Облачно, дождь, гроза"></div>
    <div class="row-item" data-tooltip="Пасмурно, небольшой дождь"></div>
    <div class="row-item" data-tooltip="Облачно"></div>
    <div class="row-item" data-tooltip="Облачно"></div>
    <div class="row-item" data-tooltip="Пасмурно"></div>
  </div>

  <div class="widget-row widget-row-chart widget-row-chart-temperature-air"
       data-row="temperature-air">
    <div class="chart">
      <div class="values">
        <div class="value"><temperature-value from-unit="c" value="17"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="17"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="16"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="16"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="21"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="21"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="19"></temperature-value></div>
        <div class="value"><temperature-value from-unit="c" value="17"></temperature-value></div>
      </div>
    </div>
  </div>

  <div class="widget-row widget-row-precipitation-bars" data-row="precipitation-bars">
    <div class="row-item"><div class="item-unit">0</div></div>
    <div class="row-item"><div class="item-unit">0</div></div>
    <div class="row-item"><div class="item-unit unit-blue">0,2</div></div>
    <div class="row-item"><div class="item-unit unit-blue">2</div></div>
    <div class="row-item"><div class="item-unit unit-blue">1,5</div></div>
    <div class="row-item"><div class="item-unit unit-blue">0,5</div></div>
    <div class="row-item"><div class="item-unit">0</div></div>
    <div class="row-item"><div class="item-unit">0</div></div>
  </div>
</body>
</html>
"""


def test_parse_page_returns_eight_slot_forecasts():
    result = parse_page(SAMPLE_HTML)
    assert result is not None
    assert len(result) == 8
    # First slot's temperature
    assert result[0]["temperature_c"] == 17.0
    # Spike slot precipitation = 2.0
    assert result[3]["precipitation_mm"] == 2.0
    # Slot with thunder description → severe class
    assert result[3]["weather_main"] == "Thunderstorm"


def test_parse_page_target_ts_steps_three_hours():
    result = parse_page(SAMPLE_HTML)
    assert result is not None
    diffs = [
        (result[i + 1]["target_ts"] - result[i]["target_ts"]).total_seconds() / 3600
        for i in range(len(result) - 1)
    ]
    assert all(abs(d - 3) < 1e-6 for d in diffs)


def test_parse_page_ignores_city_slug_numbers():
    """City slug like 'moscow-4368' must never become a temperature."""
    html = """
    <html><body>
      <a href="/weather-moscow-4368/">Moscow</a>
      <div data-row="temperature-air"><div class="values">
        <div class="value"><temperature-value value="12"></temperature-value></div>
      </div></div>
    </body></html>
    """
    result = parse_page(html)
    assert result is not None
    assert len(result) == 1
    assert -80 <= result[0]["temperature_c"] <= 60
    assert result[0]["temperature_c"] == 12.0


def test_parse_page_returns_none_on_empty_markup():
    assert parse_page("<html><body>nothing here</body></html>") is None


def test_drop_past_filters_already_happened_slots():
    """For today's grid we want only slots in the future."""
    # Yesterday — all 8 slots are in the past
    yesterday = date.today() - timedelta(days=1)
    result = parse_page(SAMPLE_HTML, base_date=yesterday, drop_past=True)
    assert result == []

    # Tomorrow — all 8 slots are in the future, drop_past has no effect
    tomorrow = date.today() + timedelta(days=1)
    result = parse_page(SAMPLE_HTML, base_date=tomorrow, drop_past=True)
    assert result is not None
    assert len(result) == 8


def test_base_date_anchors_target_ts_to_that_day():
    target = date(2030, 1, 15)
    result = parse_page(SAMPLE_HTML, base_date=target)
    assert result is not None
    assert result[0]["target_ts"] == datetime(2030, 1, 15, 0, 0, tzinfo=timezone.utc)
    assert result[-1]["target_ts"] == datetime(2030, 1, 15, 21, 0, tzinfo=timezone.utc)
