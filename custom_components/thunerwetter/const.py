"""Constants for the thunerwetter integration.

Kept free of Home Assistant imports so parser.py (pure stdlib) can use it.
"""
from __future__ import annotations

DOMAIN = "thunerwetter"

MANUFACTURER = "WsWin/thunerwetter.ch"
MODEL = "Davis Vantage Pro 2"

CONF_URL = "url"
CONF_POLL_INTERVAL = "poll_interval"

DEFAULT_URL = "https://www.thunerwetter.ch/clientraw.txt"
DEFAULT_POLL_INTERVAL = 600
MIN_POLL_INTERVAL = 60
MAX_POLL_INTERVAL = 600

# Auxiliary pages/feeds derived from the clientraw base URL. The site serves
# them as iso-8859-1; the parser anchors on ASCII-only markup so decoding with
# latin-1 is safe. WsWin publishes no JSON for these — HTML scraping is the
# only stable interface (verified 2026-09-28).
PATH_AKTUELL = "aktuell.html"
PATH_AKTUELL_SEE = "aktuell_see.html"

# Public Thingspeak channel embedded in radioaktivitaet.html. Minute-wise
# feeds with spiky values (individual rain showers) — the parser averages
# them. field1 = pulses/min, field2 = dose rate nSv/h.
THINGSPEAK_URL = "https://api.thingspeak.com/channels/412067/feeds.json?results=30"

# Sanity gate: clientraw field 0 must be exactly this, otherwise the feed
# format changed and the whole update is aborted.
MAGIC = "12345"

# Missing-value placeholder used by the WsWin feed.
MISSING = "--"

# 0-based clientraw field indices. NOTE: this is the WsWin layout of
# thunerwetter.ch, verified 2026-09-28 against the live feed and
# aktuell.html. It deliberately DIVERGES from the classic Weather Display
# spec (WD: temp at [1], gust at [3], dir at [4]) — never "fix" indices
# back to WD order without re-verifying against aktuell.html.
IDX_RAIN_RATE = 1
IDX_WIND_SPEED = 2
IDX_WIND_BEARING = 3
IDX_TEMPERATURE = 4
IDX_HUMIDITY = 5
IDX_PRESSURE = 6
IDX_RAIN_TODAY = 7
IDX_RAIN_MONTH = 8
IDX_RAIN_YEAR = 9
IDX_TEMPERATURE_INDOOR = 12
IDX_HUMIDITY_INDOOR = 13
IDX_STAMP = 32
IDX_TEMPERATURE_MAX_TODAY = 46
IDX_TEMPERATURE_MIN_TODAY = 47
IDX_CONDITION = 49
IDX_TEMPERATURE_TREND = 50
IDX_DEWPOINT = 72

# Plausibility gates.
TEMP_MIN = -60.0
TEMP_MAX = 60.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0
PRESSURE_MIN = 800.0
PRESSURE_MAX = 1200.0

# Lake water (Thunersee, -30 cm): range covers ice water to hot summer days.
WATER_TEMP_MIN = 0.0
WATER_TEMP_MAX = 40.0
# Snow line altitude in metres (can dip below zero during winter storms).
SNOW_LINE_MIN = -1000.0
SNOW_LINE_MAX = 6000.0
# Radiation dose rate nSv/h: normal 70-220, rain showers spike higher; the
# parser averages 30 minute-wise feeds first, so this only gates the mean.
RADIOACTIVITY_MAX = 10000.0
