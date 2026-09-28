"""Pure clientraw.txt parsing for thunerwetter.ch — stdlib only, no HA imports.

The feed is a single ASCII line, space-separated (~169 fields). WsWin uses
"--" as "no value" placeholder. See const.py for the verified field mapping
and the WsWin-vs-Weather-Display divergence warning.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from .const import (
    HUMIDITY_MAX,
    HUMIDITY_MIN,
    IDX_CONDITION,
    IDX_DEWPOINT,
    IDX_HUMIDITY,
    IDX_HUMIDITY_INDOOR,
    IDX_PRESSURE,
    IDX_RAIN_MONTH,
    IDX_RAIN_RATE,
    IDX_RAIN_TODAY,
    IDX_RAIN_YEAR,
    IDX_STAMP,
    IDX_TEMPERATURE,
    IDX_TEMPERATURE_INDOOR,
    IDX_TEMPERATURE_MAX_TODAY,
    IDX_TEMPERATURE_MIN_TODAY,
    IDX_TEMPERATURE_TREND,
    IDX_WIND_BEARING,
    IDX_WIND_SPEED,
    MAGIC,
    MISSING,
    PRESSURE_MAX,
    PRESSURE_MIN,
    TEMP_MAX,
    TEMP_MIN,
)

_TZ = ZoneInfo("Europe/Zurich")

# e.g. "Das_Wetter_von_Thun-28.09.2026_18:40_Uhr"
_STAMP_RE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})_(\d{1,2}):(\d{2})_Uhr\b")

_UMLAUTS = {"ae": "ä", "oe": "ö", "ue": "ü", "Ae": "Ä", "Oe": "Ö", "Ue": "Ü"}
_VOWELS = "aeiouy"


def _num(fields: list[str], idx: int, lo: float | None = None, hi: float | None = None) -> float | None:
    if idx >= len(fields):
        return None
    raw = fields[idx]
    if raw == MISSING:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    if lo is not None and value < lo:
        return None
    if hi is not None and value > hi:
        return None
    return value


def _umlauts(text: str) -> str:
    """WsWin writes umlauts as digraphs (oe -> ö).

    Only convert when not preceded by a vowel, so legit sequences like
    "neue" are left alone.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        pair = text[i : i + 2]
        prev = text[i - 1] if i > 0 else ""
        if pair in _UMLAUTS and not (prev.lower() in _VOWELS and prev.isalpha()):
            out.append(_UMLAUTS[pair])
            i += 2
            continue
        out.append(text[i])
        i += 1
    return "".join(out)


def _condition(field: str) -> str | None:
    text = field.replace("_", " ").strip()
    if text.lower().startswith("aktuell"):
        text = text[len("aktuell") :].lstrip(" :").strip()
    text = _umlauts(text).strip()
    return text or None


def _stamp(field: str) -> datetime | None:
    match = _STAMP_RE.search(field)
    if match is None:
        return None
    day, month, year, hour, minute = (int(g) for g in match.groups())
    try:
        return datetime(year, month, day, hour, minute, tzinfo=_TZ)
    except ValueError:
        return None


def parse_clientraw(raw: str) -> dict[str, Any] | None:
    """Parse a clientraw.txt line.

    Returns None if the sanity gate fails (field 0 != magic) — the caller
    must treat that as a full update failure. Individual fields that are
    missing ("--"), unparsable or implausible are simply absent from the
    result dict; the rest still updates.
    """
    fields = raw.split()
    if not fields or fields[0] != MAGIC:
        return None

    data: dict[str, Any] = {}

    if (value := _num(fields, IDX_RAIN_RATE, lo=0.0)) is not None:
        data["rain_rate"] = value
    if (value := _num(fields, IDX_WIND_SPEED, lo=0.0)) is not None:
        data["wind_speed"] = value
    if (value := _num(fields, IDX_WIND_BEARING, lo=0.0, hi=360.0)) is not None:
        data["wind_bearing"] = value
    if (value := _num(fields, IDX_TEMPERATURE, TEMP_MIN, TEMP_MAX)) is not None:
        data["temperature"] = value
    if (value := _num(fields, IDX_HUMIDITY, HUMIDITY_MIN, HUMIDITY_MAX)) is not None:
        data["humidity"] = value
    if (value := _num(fields, IDX_PRESSURE, PRESSURE_MIN, PRESSURE_MAX)) is not None:
        data["pressure"] = value
    if (value := _num(fields, IDX_RAIN_TODAY, lo=0.0)) is not None:
        data["rain_today"] = value
    if (value := _num(fields, IDX_RAIN_MONTH, lo=0.0)) is not None:
        data["rain_month"] = value
    if (value := _num(fields, IDX_RAIN_YEAR, lo=0.0)) is not None:
        data["rain_year"] = value
    if (value := _num(fields, IDX_TEMPERATURE_INDOOR, TEMP_MIN, TEMP_MAX)) is not None:
        data["temperature_indoor"] = value
    if (value := _num(fields, IDX_HUMIDITY_INDOOR, HUMIDITY_MIN, HUMIDITY_MAX)) is not None:
        data["humidity_indoor"] = value
    if IDX_STAMP < len(fields) and (value := _stamp(fields[IDX_STAMP])) is not None:
        data["last_update"] = value
    if (value := _num(fields, IDX_TEMPERATURE_MAX_TODAY, TEMP_MIN, TEMP_MAX)) is not None:
        data["temperature_max_today"] = value
    if (value := _num(fields, IDX_TEMPERATURE_MIN_TODAY, TEMP_MIN, TEMP_MAX)) is not None:
        data["temperature_min_today"] = value
    if IDX_CONDITION < len(fields) and (value := _condition(fields[IDX_CONDITION])) is not None:
        data["condition_text"] = value
    if (value := _num(fields, IDX_TEMPERATURE_TREND, TEMP_MIN, TEMP_MAX)) is not None:
        data["temperature_trend_24h"] = value
    if (
        (value := _num(fields, IDX_DEWPOINT, TEMP_MIN, TEMP_MAX)) is not None
        # Dewpoint above air temperature is physically impossible -> drop.
        and ("temperature" not in data or value <= data["temperature"])
    ):
        data["dewpoint"] = value

    return data
