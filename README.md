# thunerwetter (Home Assistant custom integration)

Home Assistant integration for the **thunerwetter.ch** weather station in
Thun, CH — a private Davis Vantage Pro 2 (WsWin) that publishes a
`clientraw.txt` feed. Polls the feed and exposes live measurements as
sensors: temperature, humidity, pressure, wind (speed/bearing), rain
(rate/today/month/year), indoor temp/humidity, dewpoint, daily min/max,
24 h trend and the station's own condition text.

Forecast and weather warnings come separately from the MeteoSwiss
integration (LNKtwo/ha-meteoswiss) — this integration is pure live-station
data.

## Installation

### HACS (recommended)

1. Add this repository to HACS as a custom repository (category:
   *Integration*).
2. Install **Thunerwetter**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/thunerwetter/` into the `custom_components/`
directory of your Home Assistant configuration and restart.

## Configuration

After the restart: **Settings → Devices & Services → Add Integration →
Thunerwetter**. The flow asks for:

- **Feed URL** — defaults to
  `https://www.thunerwetter.ch/clientraw.txt`
- **Poll interval** — 60–600 s, default **120 s** (the web feed refreshes
  about every 2 minutes; the station pushes to WU every 2.5 s, but the
  `clientraw.txt` file itself updates slower).

The feed is fetched and parsed once during setup — a bad URL or an
invalid feed is rejected with an error. Both values can be changed later
via the integration's **Configure** dialog (the entry reloads on change).

## Entities

One device (**thunerwetter**, manufacturer *WsWin/thunerwetter.ch*, model
*Davis Vantage Pro 2*) with these sensors (`sensor.thunerwetter_*`):

| Entity | Unit | Notes |
|---|---|---|
| Temperature / Indoor temperature | °C | |
| Humidity / Indoor humidity | % | |
| Pressure | hPa | station pressure |
| Wind speed | km/h | ~10 min average |
| Wind bearing | ° | 0 = north, clockwise |
| Rain rate | mm/h | 0.0 when dry |
| Rain today / this month / this year | mm | totals with `last_reset` at period start |
| Dewpoint | °C | dropped when > air temperature |
| Max/min temperature today | °C | reset daily by the station |
| Temperature trend (24 h) | °C | signed |
| Condition | text | station's own text, icon derived from it |
| Last update | timestamp | station's own timestamp (Europe/Zurich), diagnostic |

Fields that are missing (`--`), unparsable or implausible make only the
affected sensor unavailable for that cycle — the rest still updates. A
feed that fails the `12345` magic-header sanity gate aborts the whole
update (all entities unavailable) until the format is sane again.

## Data source / field mapping

The station runs **WsWin**, whose clientraw layout **diverges from the
classic Weather Display spec** (WD puts temperature at field 1, gust at 3,
direction at 4 — here: rain rate at 1, direction at 3, temperature at 4).
The mapping in `custom_components/thunerwetter/const.py` was verified on
2026-09-28 against the live feed and the live values on
`thunerwetter.ch/aktuell.html` (timestamp- and value-matched, including
"Maximum heute", "Minimum heute" and "Taupunkt"). Do not copy indices
from WD documentation, and re-verify against `aktuell.html` (same-minute
cross-check) before extending the mapping.

Plausibility gates: temperature −60…+60 °C, humidity 0–100 %, pressure
800–1200 hPa, wind/rain ≥ 0, dewpoint ≤ temperature.

## Development

```bash
pip install -r requirements-dev.txt
pytest
ruff check custom_components tests
```

`parser.py` is pure Python (stdlib only) — the fixture in
`tests/fixtures/clientraw.txt` is a real captured feed and the parser
tests assert the full verified mapping against it.

CI (`.github/workflows/validate.yml`) runs hassfest, the HACS action and
pytest + ruff. Tagging a commit with `v*` builds a release zip
(`release.yml`).

## License

Apache-2.0. Not affiliated with thunerwetter.ch or Home Assistant.
