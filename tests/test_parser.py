"""Tests for the pure clientraw parser against the captured live fixture."""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from custom_components.thunerwetter.parser import parse_clientraw

FIXTURE = Path(__file__).parent / "fixtures" / "clientraw.txt"
ZURICH = ZoneInfo("Europe/Zurich")


def parse(text: str | None = None):
    if text is None:
        text = FIXTURE.read_text(encoding="ascii")
    return parse_clientraw(text)


def replace_field(text: str, idx: int, value: str) -> str:
    fields = text.split()
    fields[idx] = value
    return " ".join(fields)


def test_fixture_parses_all_entities():
    data = parse()
    assert data == {
        "rain_rate": 0.0,
        "wind_speed": 0.9,
        "wind_bearing": 116.0,
        "temperature": 24.8,
        "humidity": 54.0,
        "pressure": 1016.0,
        "rain_today": 0.0,
        "rain_month": 31.0,
        "rain_year": 485.3,
        "temperature_indoor": 23.4,
        "humidity_indoor": 47.0,
        "last_update": datetime(2026, 9, 28, 18, 40, tzinfo=ZURICH),
        "temperature_max_today": 28.9,
        "temperature_min_today": 9.6,
        "condition_text": "leicht bewölkt",
        "temperature_trend_24h": 0.4,
        "dewpoint": 14.8,
    }


def test_missing_marker_yields_absent_key():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 4, "--")
    data = parse(raw)
    assert "temperature" not in data
    assert data["humidity"] == 54.0  # other fields still update


def test_unparsable_field_yields_absent_key():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 2, "abc")
    data = parse(raw)
    assert "wind_speed" not in data


def test_sanity_gate_rejects_wrong_magic():
    assert parse_clientraw("99999 " + FIXTURE.read_text(encoding="ascii")) is None
    assert parse_clientraw("") is None
    assert parse_clientraw("not a feed at all") is None


def test_short_feed_does_not_crash():
    data = parse_clientraw("12345 0.0 0.9 116 24.8")
    assert data == {
        "rain_rate": 0.0,
        "wind_speed": 0.9,
        "wind_bearing": 116.0,
        "temperature": 24.8,
    }


def test_temperature_plausibility_gate():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 4, "200.0")
    assert "temperature" not in parse(raw)
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 4, "-70.0")
    assert "temperature" not in parse(raw)


def test_humidity_and_pressure_plausibility_gate():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 5, "150")
    assert "humidity" not in parse(raw)
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 6, "500.0")
    assert "pressure" not in parse(raw)


def test_negative_wind_rejected():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 2, "-3.0")
    assert "wind_speed" not in parse(raw)


def test_dewpoint_above_temperature_dropped():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 72, "30.0")
    data = parse(raw)
    assert "dewpoint" not in data


def test_dewpoint_kept_without_temperature():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 4, "--")
    data = parse(raw)
    assert data["dewpoint"] == 14.8


def test_negative_temperature_trend_kept():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 50, "-1.2")
    assert parse(raw)["temperature_trend_24h"] == -1.2


def test_condition_without_prefix_and_umlaut_guard():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 49, "wolkig")
    assert parse(raw)["condition_text"] == "wolkig"
    # "ue" after a vowel must not become "ü"
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 49, "neue_Nebelfelder")
    assert parse(raw)["condition_text"] == "neue Nebelfelder"


def test_condition_empty_after_prefix():
    raw = replace_field(FIXTURE.read_text(encoding="ascii"), 49, "Aktuell_:_")
    assert "condition_text" not in parse(raw)


def test_unparsable_stamp_dropped():
    raw = replace_field(
        FIXTURE.read_text(encoding="ascii"), 32, "Das_Wetter_von_Thun"
    )
    assert "last_update" not in parse(raw)
