"""Config flow for the thunerwetter integration."""
from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_POLL_INTERVAL,
    CONF_URL,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MAX_POLL_INTERVAL,
    MIN_POLL_INTERVAL,
)
from .parser import parse_clientraw

FETCH_TIMEOUT = 30

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default=DEFAULT_URL): cv.string,
        vol.Required(CONF_POLL_INTERVAL, default=DEFAULT_POLL_INTERVAL): vol.All(
            vol.Coerce(int),
            vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
            NumberSelector(
                NumberSelectorConfig(
                    min=MIN_POLL_INTERVAL,
                    max=MAX_POLL_INTERVAL,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
        ),
    }
)


def normalize_url(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = f"https://{url}"
    return url


def feed_unique_id(url: str) -> str:
    """Stable unique id: feed host + path."""
    parts = urlparse(url)
    return f"{parts.netloc}{parts.path}"


async def async_validate_feed(hass: HomeAssistant, url: str) -> str | None:
    """Fetch + parse once. Returns an error key or None if the feed is good."""
    session = async_get_clientsession(hass)
    try:
        async with asyncio.timeout(FETCH_TIMEOUT):
            response = await session.get(url)
            response.raise_for_status()
            raw = await response.text()
    except (TimeoutError, asyncio.TimeoutError, aiohttp.ClientError, OSError):
        return "cannot_connect"
    if parse_clientraw(raw) is None:
        return "invalid_feed"
    return None


class ThunerwetterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the thunerwetter config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            user_input = {**user_input, CONF_URL: url}
            if error := await async_validate_feed(self.hass, url):
                errors["base"] = error
            else:
                await self.async_set_unique_id(feed_unique_id(url))
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Thunerwetter", data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class ThunerwetterOptionsFlow(OptionsFlow):
    """Options: URL and poll interval; the entry reloads on change."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = normalize_url(user_input[CONF_URL])
            user_input = {**user_input, CONF_URL: url}
            url_changed = url != self.config_entry.data.get(CONF_URL)
            if url_changed and (error := await async_validate_feed(self.hass, url)):
                errors["base"] = error
            if not errors:
                # Keep the original unique id so it stays stable across URL edits.
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, **user_input},
                )
                return self.async_create_entry(data={})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_URL,
                    default=self.config_entry.data.get(CONF_URL, DEFAULT_URL),
                ): cv.string,
                vol.Required(
                    CONF_POLL_INTERVAL,
                    default=self.config_entry.data.get(
                        CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_POLL_INTERVAL, max=MAX_POLL_INTERVAL),
                    NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_POLL_INTERVAL,
                            max=MAX_POLL_INTERVAL,
                            step=1,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


def async_get_options_flow(config_entry) -> ThunerwetterOptionsFlow:
    return ThunerwetterOptionsFlow()
