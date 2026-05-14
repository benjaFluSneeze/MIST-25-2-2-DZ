"""Smoke test for the Open-Meteo parser using a synthetic payload."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "ingestor"))

from src.collectors.open_meteo import _parse_hourly, _weather_code_to_main  # noqa: E402


def test_weather_code_mapping():
    assert _weather_code_to_main(0) == "Clear"
    assert _weather_code_to_main(2) == "Clouds"
    assert _weather_code_to_main(61) == "Rain"
    assert _weather_code_to_main(75) == "Snow"
    assert _weather_code_to_main(95) == "Thunderstorm"
    assert _weather_code_to_main(None) is None


def test_parse_hourly_with_sample_payload():
    payload = {
        "hourly": {
            "time": ["2024-01-01T00:00", "2024-01-01T01:00"],
            "temperature_2m": [-5.0, -4.5],
            "relative_humidity_2m": [80, 82],
            "pressure_msl": [1015, 1014],
            "wind_speed_10m": [2.0, 2.5],
            "wind_direction_10m": [180, 190],
            "cloud_cover": [100, 90],
            "precipitation": [0.0, 0.1],
            "weather_code": [3, 61],
        }
    }
    rows = _parse_hourly(payload)
    assert len(rows) == 2
    assert rows[0]["temperature_c"] == -5.0
    assert rows[0]["weather_main"] == "Clouds"
    assert rows[1]["weather_main"] == "Rain"
