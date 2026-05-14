"""Tests for the Gismeteo parser using realistic markup fixtures."""
import sys
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


def test_parse_page_returns_aggregated_forecast():
    result = parse_page(SAMPLE_HTML)
    assert result is not None
    # 8 hourly temperatures, mean = 18.0
    assert abs(result["temperature_c"] - 18.0) < 0.01
    # 0 + 0 + 0.2 + 2 + 1.5 + 0.5 + 0 + 0 = 4.2 mm
    assert abs(result["precipitation_mm"] - 4.2) < 0.01
    # Severe condition wins: Thunderstorm > Rain > Clouds
    assert result["weather_main"] == "Thunderstorm"


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
    assert -80 <= result["temperature_c"] <= 60
    assert result["temperature_c"] == 12.0


def test_parse_page_returns_none_on_empty_markup():
    assert parse_page("<html><body>nothing here</body></html>") is None


def test_condition_classification_clear_when_no_rain():
    html = """
    <html><body>
      <div data-row="icon-tooltip">
        <div class="row-item" data-tooltip="Ясно"></div>
        <div class="row-item" data-tooltip="Ясно"></div>
        <div class="row-item" data-tooltip="Облачно"></div>
      </div>
      <div data-row="temperature-air"><div class="values">
        <div class="value"><temperature-value value="20"></temperature-value></div>
      </div></div>
    </body></html>
    """
    result = parse_page(html)
    assert result is not None
    # Clear appears twice, Clouds once — most frequent without severe = Clear
    assert result["weather_main"] == "Clear"
