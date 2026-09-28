"""Data update coordinator fetching and parsing the clientraw.txt feed."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_POLL_INTERVAL,
    CONF_URL,
    DEFAULT_POLL_INTERVAL,
    DOMAIN,
)
from .parser import parse_clientraw

_LOGGER = logging.getLogger(__name__)

FETCH_TIMEOUT = 30


class ThunerwetterDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One fetch per cycle feeding all sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._url: str = entry.data[CONF_URL]
        interval: int = entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        self._session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self._url}",
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            async with asyncio.timeout(FETCH_TIMEOUT):
                response = await self._session.get(self._url)
                response.raise_for_status()
                raw = await response.text()
        except (TimeoutError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Timeout fetching {self._url}: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching {self._url}: {err}") from err

        data = parse_clientraw(raw)
        if data is None:
            # Sanity gate failed: feed format changed -> all entities unavailable.
            raise UpdateFailed(f"Feed at {self._url} failed the clientraw sanity gate")
        return data
