"""Tests for the auxiliary page parsers (water temp, snow line, radioactivity)."""
import json
from pathlib import Path

from custom_components.thunerwetter.parser import (
    parse_radioactivity,
    parse_snow_line,
    parse_water_temperature,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_water_temperature_parses_current_and_average():
    raw = (FIXTURES / "aktuell_see.html").read_text(encoding="latin-1")
    assert parse_water_temperature(raw) == {
        "water_temperature": 20.0,
        "water_temperature_avg_24h": 19.1,
    }


def test_water_temperature_ignores_style_digits():
    raw = "<html><style>.a{font-size: 10pt;}</style><body><span>20.0</span></body></html>"
    assert parse_water_temperature(raw) == {"water_temperature": 20.0}


def test_water_temperature_gates_implausible_values():
    raw = "<body><span>99.0</span><span>19.1</span></body>"
    assert parse_water_temperature(raw) == {"water_temperature_avg_24h": 19.1}


def test_water_temperature_empty_page():
    assert parse_water_temperature("<html><body></body></html>") == {}


def test_snow_line_parses_aktuell_page():
    raw = (FIXTURES / "aktuell.html").read_text(encoding="latin-1")
    assert parse_snow_line(raw) == {"snow_line": 3210.0}


def test_snow_line_negative_and_missing():
    raw = "<td>Schneefallgrenze</td><td>-50 m</td>"
    assert parse_snow_line(raw) == {"snow_line": -50.0}
    assert parse_snow_line("<td>Regen</td><td>3210 m</td>") == {}
    raw = "<td>Schneefallgrenze</td><td>999999 m</td>"
    assert parse_snow_line(raw) == {}


def test_radioactivity_averages_feeds_and_skips_gaps():
    raw = (FIXTURES / "thingspeak.json").read_text(encoding="utf-8")
    data = parse_radioactivity(raw)
    # field2 values 70, 1273, 90, None -> mean = 477.666... -> 477.7
    assert data["radioactivity"] == 477.7
    # field1 values 12, 2, 11, "--" -> mean = 8.333... -> 8.3
    assert data["radioactivity_cpm"] == 8.3


def test_radioactivity_empty_and_broken_json():
    empty = json.dumps({"channel": {}, "feeds": []})
    assert parse_radioactivity(empty) == {}
    assert parse_radioactivity("not json at all") == {}
