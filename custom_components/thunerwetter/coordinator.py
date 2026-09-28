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
    PATH_AKTUELL,
    PATH_AKTUELL_SEE,
    THINGSPEAK_URL,
)
from .parser import (
    parse_clientraw,
    parse_radioactivity,
    parse_snow_line,
    parse_water_temperature,
)

_LOGGER = logging.getLogger(__name__)

FETCH_TIMEOUT = 30


class ThunerwetterDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """One fetch per cycle feeding all sensors."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self._url: str = entry.data[CONF_URL]
        # The auxiliary pages live next to clientraw.txt on the same host.
        self._base_url = self._url.rsplit("/", 1)[0] + "/"
        interval: int = entry.data.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
        self._session = async_get_clientsession(hass)
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {self._url}",
            update_interval=timedelta(seconds=interval),
        )

    async def _fetch_text(self, url: str, *, latin1: bool = False) -> str:
        response = await self._session.get(url)
        response.raise_for_status()
        # The WsWin pages declare no charset and are iso-8859-1; decoding with
        # latin-1 never fails and the parser only anchors on ASCII markup.
        return await response.text(encoding="latin-1" if latin1 else None)

    async def _fetch_extras(self, data: dict[str, Any]) -> None:
        """Fetch the auxiliary pages; a failure only drops those keys."""

        async def safe(coro, parser):
            try:
                return parser(await coro)
            except (TimeoutError, asyncio.TimeoutError, aiohttp.ClientError) as err:
                _LOGGER.warning("Auxiliary fetch failed, skipping its values: %s", err)
                return {}

        lake, current, radiation = await asyncio.gather(
            safe(self._fetch_text(self._base_url + PATH_AKTUELL_SEE, latin1=True), parse_water_temperature),
            safe(self._fetch_text(self._base_url + PATH_AKTUELL, latin1=True), parse_snow_line),
            safe(self._fetch_text(THINGSPEAK_URL), parse_radioactivity),
            return_exceptions=False,
        )
        data.update(lake)
        data.update(current)
        data.update(radiation)

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

        try:
            async with asyncio.timeout(FETCH_TIMEOUT):
                await self._fetch_extras(data)
        except TimeoutError:
            _LOGGER.warning("Auxiliary fetches timed out, skipping their values")

        return data
