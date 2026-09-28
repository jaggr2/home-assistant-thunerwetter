"""Tests for the sensor entity definitions (no full HA test harness needed)."""
import pytest

pytest.importorskip("homeassistant")

from homeassistant.const import UnitOfVolumetricFlux

from custom_components.thunerwetter.sensor import (
    SENSOR_DEFS,
    ThunerwetterSensor,
    condition_icon,
)


class FakeCoordinator:
    last_update_success = True

    def __init__(self, data):
        self.data = data


class FakeEntry:
    entry_id = "test-entry-123"


def make_sensors(data):
    coordinator = FakeCoordinator(data)
    return {d.key: ThunerwetterSensor(coordinator, "test-entry-123", d) for d in SENSOR_DEFS}


def test_all_spec_entities_present():
    assert {d.key for d in SENSOR_DEFS} == {
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "wind_bearing",
        "rain_rate",
        "rain_today",
        "rain_month",
        "rain_year",
        "temperature_indoor",
        "humidity_indoor",
        "dewpoint",
        "temperature_max_today",
        "temperature_min_today",
        "temperature_trend_24h",
        "condition_text",
        "last_update",
    }


def test_device_classes_and_units():
    sensors = make_sensors({})
    s = sensors

    assert s["temperature"].device_class.value == "temperature"
    assert s["temperature"].native_unit_of_measurement == "°C"
    assert s["temperature"].state_class.value == "measurement"

    assert s["pressure"].native_unit_of_measurement == "hPa"
    assert s["wind_speed"].native_unit_of_measurement == "km/h"
    assert s["wind_bearing"].native_unit_of_measurement == "°"
    assert s["wind_bearing"].device_class is None

    assert s["rain_rate"].device_class.value == "precipitation_intensity"
    assert (
        s["rain_rate"].native_unit_of_measurement
        == UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR
    )
    for key in ("rain_today", "rain_month", "rain_year"):
        assert s[key].device_class.value == "precipitation"
        assert s[key].native_unit_of_measurement == "mm"
        assert s[key].state_class.value == "total"

    assert s["last_update"].device_class.value == "timestamp"
    assert s["last_update"].entity_category.value == "diagnostic"
    assert s["condition_text"].device_class is None
    assert s["condition_text"].state_class is None


def test_device_info_single_device():
    sensor = make_sensors({})["temperature"]
    info = sensor.device_info
    assert info["identifiers"] == {("thunerwetter", "test-entry-123")}
    assert info["name"] == "thunerwetter"
    assert info["manufacturer"] == "WsWin/thunerwetter.ch"
    assert info["model"] == "Davis Vantage Pro 2"


def test_native_value_and_availability():
    sensors = make_sensors({"temperature": 24.8})
    assert sensors["temperature"].native_value == 24.8
    assert sensors["temperature"].available

    # Missing key -> unavailable, but other entities with values stay available.
    assert not sensors["humidity"].available
    assert sensors["temperature"].available


def test_last_reset_periods():
    sensors = make_sensors({})
    for key in ("rain_rate", "temperature", "last_update", "condition_text"):
        assert sensors[key].last_reset is None

    today_reset = sensors["rain_today"].last_reset
    assert (today_reset.hour, today_reset.minute, today_reset.second) == (0, 0, 0)

    month_reset = sensors["rain_month"].last_reset
    assert month_reset.day == 1

    year_reset = sensors["rain_year"].last_reset
    assert (year_reset.month, year_reset.day) == (1, 1)


def test_condition_icons():
    assert condition_icon("leicht bewölkt") == "mdi:weather-cloudy"
    assert condition_icon("sonnig") == "mdi:weather-sunny"
    assert condition_icon("Regen") == "mdi:weather-rainy"
    assert condition_icon("Gewitter") == "mdi:weather-lightning"
    assert condition_icon("heiter") == "mdi:weather-partly-cloudy"
    assert condition_icon("Irgendwas Komisches") == "mdi:weather-cloudy"
    assert condition_icon(None) is None


def test_condition_icon_on_sensor():
    sensors = make_sensors({"condition_text": "sonnig"})
    assert sensors["condition_text"].icon == "mdi:weather-sunny"
    assert sensors["temperature"].icon is None
