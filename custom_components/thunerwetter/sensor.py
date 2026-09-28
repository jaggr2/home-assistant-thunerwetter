"""Sensor platform for the thunerwetter integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import ThunerwetterDataUpdateCoordinator


@dataclass(frozen=True)
class SensorDef:
    key: str
    translation_key: str
    device_class: SensorDeviceClass | None = None
    native_unit: str | None = None
    state_class: SensorStateClass | None = None
    entity_category: EntityCategory | None = None
    # Rain totals reset at period start -> expose last_reset for statistics.
    reset_period: Literal["day", "month", "year"] | None = None


SENSOR_DEFS: tuple[SensorDef, ...] = (
    SensorDef(
        "temperature",
        "temperature",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "humidity",
        "humidity",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "pressure",
        "pressure",
        SensorDeviceClass.PRESSURE,
        UnitOfPressure.HPA,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "wind_speed",
        "wind_speed",
        SensorDeviceClass.WIND_SPEED,
        UnitOfSpeed.KILOMETERS_PER_HOUR,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "wind_bearing",
        "wind_bearing",
        None,
        DEGREE,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "rain_rate",
        "rain_rate",
        SensorDeviceClass.PRECIPITATION_INTENSITY,
        UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "rain_today",
        "rain_today",
        SensorDeviceClass.PRECIPITATION,
        UnitOfPrecipitationDepth.MILLIMETERS,
        SensorStateClass.TOTAL,
        reset_period="day",
    ),
    SensorDef(
        "rain_month",
        "rain_month",
        SensorDeviceClass.PRECIPITATION,
        UnitOfPrecipitationDepth.MILLIMETERS,
        SensorStateClass.TOTAL,
        reset_period="month",
    ),
    SensorDef(
        "rain_year",
        "rain_year",
        SensorDeviceClass.PRECIPITATION,
        UnitOfPrecipitationDepth.MILLIMETERS,
        SensorStateClass.TOTAL,
        reset_period="year",
    ),
    SensorDef(
        "temperature_indoor",
        "temperature_indoor",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "humidity_indoor",
        "humidity_indoor",
        SensorDeviceClass.HUMIDITY,
        PERCENTAGE,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "dewpoint",
        "dewpoint",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "temperature_max_today",
        "temperature_max_today",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "temperature_min_today",
        "temperature_min_today",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef(
        "temperature_trend_24h",
        "temperature_trend_24h",
        SensorDeviceClass.TEMPERATURE,
        UnitOfTemperature.CELSIUS,
        SensorStateClass.MEASUREMENT,
    ),
    SensorDef("condition_text", "condition_text"),
    SensorDef(
        "last_update",
        "last_update",
        SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)

# Substring -> icon, matched against the lowercased condition text.
_CONDITION_ICONS: tuple[tuple[str, str], ...] = (
    ("gewitter", "mdi:weather-lightning"),
    ("schnee", "mdi:weather-snowy"),
    ("regen", "mdi:weather-rainy"),
    ("nebel", "mdi:weather-fog"),
    ("sonnig", "mdi:weather-sunny"),
    ("heiter", "mdi:weather-partly-cloudy"),
    ("wolken", "mdi:weather-cloudy"),
    ("bewölkt", "mdi:weather-cloudy"),
    ("bedeckt", "mdi:weather-cloudy"),
)


def condition_icon(text: str | None) -> str | None:
    if not text:
        return None
    lowered = text.lower()
    for needle, icon in _CONDITION_ICONS:
        if needle in lowered:
            return icon
    return "mdi:weather-cloudy"


class ThunerwetterSensor(
    CoordinatorEntity[ThunerwetterDataUpdateCoordinator], SensorEntity
):
    """One sensor reading from the shared coordinator data dict."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ThunerwetterDataUpdateCoordinator,
        entry_id: str,
        desc: SensorDef,
    ) -> None:
        super().__init__(coordinator)
        self._desc = desc
        self._attr_unique_id = f"{entry_id}-{desc.key}"
        self._attr_translation_key = desc.translation_key
        self._attr_device_class = desc.device_class
        self._attr_native_unit_of_measurement = desc.native_unit
        self._attr_state_class = desc.state_class
        self._attr_entity_category = desc.entity_category
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="thunerwetter",
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def native_value(self):
        return self.coordinator.data.get(self._desc.key)

    @property
    def available(self) -> bool:
        # Missing ("--" or implausible) field for this cycle -> unavailable,
        # the other entities still update.
        return super().available and self.coordinator.data.get(self._desc.key) is not None

    @property
    def last_reset(self):
        if self._desc.reset_period is None:
            return None
        now = dt_util.now()
        if self._desc.reset_period == "day":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if self._desc.reset_period == "month":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    @property
    def icon(self) -> str | None:
        if self._desc.key == "condition_text":
            return condition_icon(self.coordinator.data.get("condition_text"))
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: ThunerwetterDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        ThunerwetterSensor(coordinator, entry.entry_id, desc) for desc in SENSOR_DEFS
    )
