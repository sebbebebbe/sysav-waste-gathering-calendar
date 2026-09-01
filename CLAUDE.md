# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Homey app **Sophämtningskalendern** (`com.hibbisoft.garbagecalendar`) — tracks garbage pickup dates. Homey SDK 3, Python runtime 3.14, `local` platform only, minimum Homey firmware `>=13.0.0`.

## Data flow

The app wraps the Sysav public pickup-schedule API (same endpoint the old Home Assistant `sensor.sysav` integration used). There is **one generic driver** (`sysav_bin`): each device represents a single `wasteType` (Kärl 1, Matavfall, Trädgårdsavfall, …) at one address.

- `app.py` (`SysavApp`) owns the HTTP call + a 55-minute in-memory cache keyed by `street|number|city`, exposed to drivers/devices as `self.homey.app.fetch_schedule(street, number, city, force=False)`. All devices at the same address share one request per hour.
- `drivers/sysav_bin/driver.py` handles pairing: `start.html` collects street/number/city, driver calls `fetch_schedule(..., force=True)`, and `on_list_devices` returns one entry per `wasteType` in the response. Device id is `_slug(street)_slug(number)_slug(city)_slug(wasteType)`; settings carry the address + waste type (driver does not store them in `data`, so they can be edited if Sysav renames a bin).
- `drivers/sysav_bin/device.py` polls hourly via `asyncio.ensure_future(self._poll_loop())` started in `on_init`, matches its `waste_type` setting against the cached response, parses `nextPickupDate`, and writes `next_pickup_date` + `days_until_pickup` capabilities. Trigger cards fire on transitions (`pickup_tomorrow` when days becomes 1, `pickup_today` when 0, `pickup_date_changed` when the date string changes).
- Flow condition `pickup_in_days` is registered in `SysavApp.on_init` via `self.homey.flow.get_condition_card(...).register_run_listener(...)`. Device-scoped triggers are fired from the device by `self.homey.flow.get_trigger_card(card_id).trigger(self, tokens, {})` — passing `self` is what scopes them to the calling device.

Custom capabilities (`next_pickup_date`, `days_until_pickup`) live under `.homeycompose/capabilities/`. All device-scoped flow cards include `{"type": "device", "name": "device", "filter": "driver_id=sysav_bin"}` in their `args`.

## Architecture

This is a Homey Compose app. The important consequence:

- **`app.json` is generated — never edit it.** It is compiled from `.homeycompose/app.json` plus the per-feature files under `.homeycompose/{capabilities,drivers,flow,discovery,screensavers,signals}/`. Make changes in `.homeycompose/` and let the Homey CLI regenerate `app.json`.
- Driver manifests live in `.homeycompose/drivers/<driver_id>/driver.compose.json` (plus `settings/` and `templates/` for shared fragments); the driver's Python code goes in `drivers/<driver_id>/device.py` and `driver.py`.
- Flow cards are split into one JSON file per card under `.homeycompose/flow/{actions,conditions,triggers}/`.
- `homey_export = MyApp` at the bottom of `app.py` is the required Homey SDK entry point — the class is discovered via this name.

## Commands

This project uses the Homey CLI (`homey`). From the project root on Windows (bash shell):

- `homey app run` — run the app on a paired Homey in dev mode (live reload on file changes).
- `homey app install` — build and install the app to your Homey.
- `homey app validate -l debug` (or `publish`/`verified`) — validate the compiled `app.json` against the SDK schema at the chosen level.
- `homey app build` — produce a `.homeybuild/` bundle without installing.
- `homey app publish` — publish to the Homey App Store.

There is no test suite, linter, or build script beyond the Homey CLI. Python dependencies (if added) go in `requirements.txt` at the project root.

## Files to be aware of

- `env.json` (gitignored) — local environment/secrets consumed by the Homey runtime via `self.homey.env`.
- `.homeybuild/` (gitignored) — CLI build output.
- `.homeychangelog.json` — user-facing changelog per version; update when bumping `version` in `.homeycompose/app.json`.
