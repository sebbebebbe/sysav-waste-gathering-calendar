import asyncio
import json
import os
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from homey.app import App


_CA_BUNDLE = os.path.join(os.path.dirname(__file__), "assets", "cacert.pem")
_SSL_CONTEXT = ssl.create_default_context(cafile=_CA_BUNDLE)


_SYSAV_URL = (
    "https://ca-swec-sysav-public-edp-prod.bluedune-a5ae63ed"
    ".swedencentral.azurecontainerapps.io/api/PickupSchedules/foraddress/"
)
_CACHE_TTL_SECONDS = 55 * 60
_HTTP_TIMEOUT_SECONDS = 20


class SysavApp(App):

    _cache: dict[str, tuple[float, list]]
    _locks: dict[str, asyncio.Lock]

    async def on_init(self) -> None:
        await super().on_init()
        self._cache = {}
        self._locks = {}
        self._register_flow_conditions()
        self.log("Sysav app initialized")

    def _register_flow_conditions(self) -> None:
        async def _pickup_in_days(args, state) -> bool:
            device = args.get("device")
            want = args.get("days")
            if device is None or want is None:
                return False
            current = device.get_capability_value("days_until_pickup")
            try:
                return int(current) == int(want)
            except (TypeError, ValueError):
                return False

        try:
            self.homey.flow.get_condition_card("pickup_in_days") \
                .register_run_listener(_pickup_in_days)
        except Exception as e:
            self.log(f"Flow condition registration failed: {e}")

    async def fetch_schedule(
        self,
        street_name: str,
        street_number: str,
        city: str,
        force: bool = False,
    ) -> list:
        key = f"{street_name.strip().lower()}|{street_number.strip().lower()}|{city.strip().lower()}"
        now = time.monotonic()

        if not force:
            cached = self._cache.get(key)
            if cached and now - cached[0] < _CACHE_TTL_SECONDS:
                return cached[1]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            cached = self._cache.get(key)
            if not force and cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
                return cached[1]

            url = _build_url(street_name, street_number, city)
            self.log(f"Sysav GET {url}")
            data = await asyncio.to_thread(_fetch_sync, url)
            self._cache[key] = (time.monotonic(), data)
            return data


def _build_url(street_name: str, street_number: str, city: str) -> str:
    address = urllib.parse.quote(f"{street_name} {street_number}, {city}")
    return f"{_SYSAV_URL}{address}"


def _fetch_sync(url: str) -> list:
    req = urllib.request.Request(url=url)
    req.add_header("Accept", "application/json, text/javascript, */*; q=0.01")
    try:
        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT_SECONDS, context=_SSL_CONTEXT) as resp:
            payload = json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Sysav API HTTP {e.code}") from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"Sysav API unreachable: {e.reason}") from e
    if not isinstance(payload, list):
        return []
    return payload


homey_export = SysavApp
