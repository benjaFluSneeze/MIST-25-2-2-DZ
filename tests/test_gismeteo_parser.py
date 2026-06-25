"""Tests for the Gismeteo parser using realistic markup fixtures."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "ingestor"))

from src.collectors.gismeteo_parser import parse_page  # noqa: E402


def _sample_html(base_utc: datetime) -> str:
    """Build a fake Gismeteo page where slot 0 = base_utc, then +3h each."""
    timestamps = [int((base_utc + timedelta(hours=i * 3)).timestamp()) for i in range(8)]
    time_strip = "".join(
        f"""
        <div class="row-item" title="Прогноз от: ..., (UTC)">
            <time-value timestamp="{ts}" format="H:mm" />
        </div>"""
        for ts in timestamps
    )
    return f"""
    <html><body>
      <a href="/weather-moscow-4368/">Moscow</a>

      <div class="widget-row widget-row-datetime-time">
        {time_strip}
      </div>

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
        <div class="chart"><div class="values">
          <div class="value"><temperature-value value="17"></temperature-value></div>
          <div class="value"><temperature-value value="17"></temperature-value></div>
          <div class="value"><temperature-value value="16"></temperature-value></div>
          <div class="value"><temperature-value value="16"></temperature-value></div>
          <div class="value"><temperature-value value="21"></temperature-value></div>
          <div class="value"><temperature-value value="21"></temperature-value></div>
          <div class="value"><temperature-value value="19"></temperature-value></div>
          <div class="value"><temperature-value value="17"></temperature-value></div>
        </div></div>
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
    </body></html>
    """


def test_parse_page_returns_eight_slot_forecasts():
    base = datetime(2030, 1, 15, 0, 0, tzinfo=timezone.utc)
    result = parse_page(_sample_html(base))
    assert result is not None
    assert len(result) == 8
    assert result[0]["temperature_c"] == 17.0
    assert result[3]["precipitation_mm"] == 2.0
    # Slot 3's tooltip contains "гроза" → Thunderstorm
    assert result[3]["weather_main"] == "Thunderstorm"


def test_parse_page_target_ts_three_hours_apart_in_utc():
    base = datetime(2030, 1, 15, 6, 0, tzinfo=timezone.utc)
    result = parse_page(_sample_html(base))
    assert result is not None
    assert result[0]["target_ts"] == base
    assert result[-1]["target_ts"] == base + timedelta(hours=21)
    diffs = [
        (result[i + 1]["target_ts"] - result[i]["target_ts"]).total_seconds() / 3600
        for i in range(len(result) - 1)
    ]
    assert all(abs(d - 3) < 1e-6 for d in diffs)


def test_parse_page_returns_none_when_no_slots():
    assert parse_page("<html><body>nothing here</body></html>") is None


def test_drop_past_filters_already_happened_slots():
    # All 8 slots in the past (started a week ago)
    past = datetime.now(timezone.utc) - timedelta(days=7)
    result = parse_page(_sample_html(past), drop_past=True)
    assert result == []

    # All 8 slots in the future (start tomorrow)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    result = parse_page(_sample_html(future), drop_past=True)
    assert result is not None
    assert len(result) == 8


def test_uses_explicit_utc_from_html_not_city_local():
    """The same temperatures attached to slots that say UTC 21:00 should
    yield target_ts == 21:00 UTC, regardless of any city tz the parser sees.
    """
    base = datetime(2030, 6, 15, 21, 0, tzinfo=timezone.utc)
    result = parse_page(_sample_html(base))
    assert result is not None
    assert result[0]["target_ts"] == base
    assert result[0]["target_ts"].tzinfo is timezone.utc
