# thunerwetter (Home Assistant custom integration)

Home Assistant integration for the **thunerwetter.ch** weather station in
Thun, CH — a private Davis Vantage Pro 2 (WsWin) that publishes a
`clientraw.txt` feed. Polls the feed and exposes live measurements as
sensors: temperature, humidity, pressure, wind (speed/bearing), rain
(rate/today/month/year), indoor temp/humidity, dewpoint, daily min/max,
24 h trend and the station's own condition text.

> WIP — see [AGENTS.md](AGENTS.md) for the full spec and the verified
> clientraw field mapping (WsWin diverges from the classic Weather Display
> layout!).

Forecast/weather-warnings come separately from the MeteoSwiss integration
(LNKtwo/ha-meteoswiss) — this integration is pure live-station data.

## License

Apache-2.0. Not affiliated with thunerwetter.ch or Home Assistant.
