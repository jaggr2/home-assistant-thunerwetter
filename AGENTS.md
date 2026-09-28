# AGENTS.md — operating guide for this repo (humans + AI agents)

Home Assistant custom integration for **thunerwetter.ch** — the private Davis
Vantage Pro 2 weather station in Thun, CH (562 m, operated by Stoller Roger,
WsWin software). The station publishes a WsWin-style `clientraw.txt` feed;
this integration polls it and exposes the measured values as HA sensor
entities. It is **not** a forecast integration (forecasts come from
MeteoSwiss/other integrations).

Model repo for architecture/CI: `jaggr2/home-assistant-value-pdu` — copy its
structure, config-flow + coordinator pattern, HACS metadata and workflows.

## Repo layout (target)

```
custom_components/thunerwetter/
  __init__.py        # config entry setup/unload, coordinator wiring
  config_flow.py     # user step: URL + poll interval; options flow: interval
  const.py           # defaults, clientraw field indices, domain data keys
  coordinator.py     # DataUpdateCoordinator fetching + parsing clientraw.txt
  parser.py          # pure clientraw parsing (unit-testable, no HA imports)
  sensor.py          # sensor platform, one device, all entities
  manifest.json
  strings.json + translations/en.json
hacs.json
README.md
LICENSE              # Apache-2.0 (match value-pdu)
.github/workflows/validate.yml   # hassfest + hacs/action (category: integration)
.github/workflows/release.yml    # on tag → release with the component zip
tests/
  fixtures/clientraw.txt          # real captured feed (see below)
  test_parser.py, test_sensor.py
pytest.ini, requirements-dev.txt, .gitignore, .gitattributes (LF)
```

## Data source facts (verified 2026-09-28)

- Feed: `https://www.thunerwetter.ch/clientraw.txt` — single ASCII line,
  **space-separated fields, ~169 fields**, `--` used as "no value" placeholder.
- Update cycle ≈ **2 minutes** (station also pushes to Weather Underground
  every 2.5 s as `IBERNTHU4`/`IBERNTHU5`, but the web feed refreshes slower).
- Default poll interval: **120 s**, minimum 60 s, maximum 600 s.
- The station runs **WsWin** (not Weather Display) — its clientraw layout
  **diverges from the classic WD spec**. Do NOT copy field indices from WD
  documentation. Use the empirically verified mapping below only.

## Verified clientraw field mapping (0-based index)

Verified on 2026-09-28 against the live feed and the live values on
`thunerwetter.ch/aktuell.html` (timestamp- and value-matched):

| Index | Value | Unit / notes |
|---|---|---|
| 0 | `12345` | magic header — sanity gate, reject feed otherwise |
| 1 | rain rate | mm/h (0.0 when dry) |
| 2 | wind speed average | km/h (≈ 10-min average) |
| 3 | wind direction | degrees (0=north, clockwise) |
| 4 | **temperature outdoor** | °C |
| 5 | humidity outdoor | % |
| 6 | pressure (station) | hPa |
| 7 | rain today | mm |
| 8 | rain current month | mm |
| 9 | rain current year | mm |
| 12 | temperature indoor | °C |
| 13 | humidity indoor | % |
| 32 | station name + timestamp | e.g. `Das_Wetter_von_Thun-28.09.2026_18:38_Uhr` — parse as `last update` datetime (Europe/Zurich) |
| 46 | temperature max today | °C (matched website "Maximum heute") |
| 47 | temperature min today | °C (matched website "Minimum heute") |
| 49 | condition text | e.g. `Aktuell_:_leicht_bewoelkt__` — strip `Aktuell :` prefix, underscores→spaces → "leicht bewölkt" |
| 50 | temperature trend | °C per 24 h, may carry `+`/`-` sign |
| 72 | dewpoint | °C (matched website "Taupunkt") |

**Do not use any other field.** Indices 15, 23, 24, 29–31, 34, 44, 45, 71, 73
and the long numeric series look plausible but could **not** be verified
against the website — mapping them risks publishing wrong data. If in doubt,
extend the mapping only with a fresh same-minute cross-check against
`aktuell.html` (the README documents how).

Parser rules:

- Fields may be `--` (missing) or unparsable → that sensor reports
  `unavailable` for this cycle, others still update.
- Sanity gate: field 0 == `12345`, else abort the whole update (format
  change → all entities unavailable, log a warning once).
- Temperature plausibility: −60…+60 °C; humidity 0–100; pressure 800–1200
  hPa; wind ≥ 0; dewpoint ≤ temperature (else drop dewpoint).

## Entities

Single device **thunerwetter** (`manufacturer: WsWin/thunerwetter.ch`,
`model: Davis Vantage Pro 2`). All sensors `entity_category: diagnostic` only
where genuinely diagnostic (last update). Suggested set:

| Entity (`sensor.thunerwetter_*`) | device_class | unit | state_class |
|---|---|---|---|
| temperature | temperature | °C | measurement |
| humidity | humidity | % | measurement |
| pressure | pressure | hPa | measurement |
| wind_speed | wind_speed | km/h | measurement |
| wind_bearing | — | ° | measurement |
| rain_rate | precipitation_intensity | mm/h | measurement |
| rain_today / rain_month / rain_year | precipitation | mm | total (today) / total (month/year, last_reset at period start) |
| temperature_indoor | temperature | °C | measurement |
| humidity_indoor | humidity | % | measurement |
| dewpoint | temperature | °C | measurement |
| temperature_max_today / temperature_min_today | temperature | °C | measurement (resets daily) |
| temperature_trend_24h | temperature | °C | measurement |
| condition_text | — | text state, icon from text | — |
| last_update | timestamp | — | — |

Use modern units/enums (`UnitOfTemperature.CELSIUS`, `UnitOfPressure.HPA`,
`UnitOfPrecipitationIntensity.MILLIMETERS_PER_HOUR`, ...) — HA ≥ 2026.1 /
Python 3.13, no deprecated constants. `has_entity_name: true`.

Optional stretch (phase 2, only after sensors work): a `weather` entity built
from these sensors with the condition text mapped to HA conditions. Forecast
is out of scope — the MeteoSwiss integration (LNKtwo/ha-meteoswiss) covers it.

## Config flow

- User step: **URL** (default `https://www.thunerwetter.ch/clientraw.txt`)
  and **poll interval** (default 120 s). Validate by fetching + parsing once
  before creating the entry; on failure show a connection error.
- Options flow: poll interval (+ URL) — reload the entry on change
  (same pattern as value-pdu).
- Unique ID: the feed host+path (stable across URL edits).

## Conventions

- Everything textual is **LF** (`.gitattributes: * text eol=lf`). Never
  commit CRLF. Never commit secrets — the integration needs none.
- Parser (`parser.py`) is pure Python (stdlib only), no HA imports — this is
  what the tests exercise. `requirements` in manifest stays `[]` (use
  `aiohttp` from HA core for fetching).
- Comments only where non-obvious (e.g. the clientraw mapping divergence);
  no comment noise, no docstrings on trivial code.
- Coordinator: one fetch per cycle feeding all sensors; store parsed dict in
  `coordinator.data`; sensors read from it (value-pdu pattern).
- Errors: `aiohttp` timeouts/HTTP errors → `UpdateFailed`; never crash the
  coordinator on a single bad feed.

## Verification (run before pushing)

```bash
pip install -r requirements-dev.txt   # pytest, homeassistant (for hassfest-type checks), ruff
pytest                                # parser tests against the fixture
ruff check custom_components tests
```

CI must pass: hassfest (manifest schema!) and the HACS action
(`hacs.json`: `{"name": "Thunerwetter", "render_readme": true, "homeassistant": "2026.1.0"}`).
Match `manifest.json` key set of value-pdu (domain `thunerwetter`, `name`,
`codeowners: ["@jaggr2"]`, `config_flow: true`, `documentation`/`issue_tracker`
→ this repo, `integration_type: service`, `iot_class: local_polling`,
`requirements: []`, `version`). hassfest rejects missing/unknown keys —
validate locally if possible.

## Dashboard notes (downstream, repo: home-control-server-config)

Entities surface as `sensor.thunerwetter_*`. The rack dashboard
(`dashboard-rack`, storage) gets a weather section there; remember the
sections-view gotcha: conditional cards silently drop cards whose entities do
not exist yet — an "install the integration" hint must be an unconditional
markdown with a Jinja existence guard.

## Known pitfall: WsWin vs Weather Display field order

Classic WD clientraw has temperature at [1], gust at [3], direction at [4].
**WsWin here does not** ([1] = rain rate, [3] = direction, [4] = temperature —
proven by the "min today" impossibility test: [1] read 0.0 °C while the
website reported today's minimum as 9.6 °C). Never "fix" the mapping back to
WD order without re-verifying against `aktuell.html` — that check is the
single source of truth for this mapping.
