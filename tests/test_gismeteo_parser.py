"""Regression tests for the Gismeteo parser sanity checks."""
import sys
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "ingestor"))

from src.collectors.gismeteo_parser import _extract_temps  # noqa: E402


def test_temp_extractor_rejects_city_slug_numbers():
    """Slug like 'moscow-4368' must not be parsed as -4368 °C."""
    html = """
    <html><body>
      <div class="header"><a href="/weather-moscow-4368/">Moscow</a></div>
      <div class="temperature"><span class="value">12°</span></div>
      <div class="temperature"><span class="value">15°</span></div>
    </body></html>
    """
    soup = BeautifulSoup(html, "lxml")
    temps = _extract_temps(soup)
    assert all(-80 <= t <= 60 for t in temps), f"Got out-of-range temps: {temps}"
    assert temps  # at least one real temp parsed


def test_temp_extractor_returns_empty_on_bad_markup():
    soup = BeautifulSoup("<html><body>no weather here</body></html>", "lxml")
    assert _extract_temps(soup) == []
