import asyncio
from datetime import date, datetime

from homey.device import Device


_POLL_INTERVAL_SECONDS = 60 * 60


def _parse_pickup_date(raw) -> date | None:
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    if "T" in text:
        text = text.split("T", 1)[0]
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


class SysavBinDevice(Device):

    _poll_task: asyncio.Task | None = None
    _last_date_iso: str | None = None
    _last_days: int | None = None

    async def on_init(self) -> None:
        await super().on_init()
        self.log(f"Device init — {self.get_setting('waste_type')} @ {self._address()}")
        await self._refresh()
        self._poll_task = asyncio.ensure_future(self._poll_loop())

    async def on_deleted(self) -> None:
        if self._poll_task and not self._poll_task.done():
            self._poll_task.cancel()
        self._poll_task = None

    async def _poll_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                return
            try:
                await self._refresh()
            except Exception as e:
                self.log(f"Poll error: {e}")

    def _address(self) -> tuple[str, str, str]:
        return (
            self.get_setting("street_name") or "",
            self.get_setting("street_number") or "",
            self.get_setting("city") or "",
        )

    async def _refresh(self) -> None:
        waste_type = self.get_setting("waste_type")
        street_name, street_number, city = self._address()
        if not (waste_type and street_name and street_number and city):
            await self.set_unavailable("Missing address or waste type")
            return

        try:
            schedule = await self.homey.app.fetch_schedule(
                street_name, street_number, city
            )
        except Exception as e:
            self.log(f"Fetch failed: {e}")
            await self.set_unavailable(str(e))
            return

        entry = next(
            (e for e in schedule if (e.get("wasteType") or e.get("WasteType")) == waste_type),
            None,
        )
        if not entry:
            await self.set_unavailable("Waste type no longer returned by Sysav")
            return

        pickup = _parse_pickup_date(entry.get("nextPickupDate") or entry.get("NextPickupDate"))
        if not pickup:
            await self.set_unavailable("No pickup date available")
            return

        await self.set_available()
        days_until = max(0, (pickup - date.today()).days)
        iso = pickup.isoformat()

        prev_iso = self._last_date_iso
        prev_days = self._last_days

        await self._set("next_pickup_date", iso)
        await self._set("days_until_pickup", days_until)

        self._last_date_iso = iso
        self._last_days = days_until

        tokens = {
            "waste_type": waste_type,
            "next_pickup_date": iso,
            "days_until_pickup": days_until,
        }

        if prev_iso is not None and prev_iso != iso:
            await self._trigger("pickup_date_changed", tokens)

        if prev_days is not None:
            if prev_days != 1 and days_until == 1:
                await self._trigger("pickup_tomorrow", tokens)
            if prev_days != 0 and days_until == 0:
                await self._trigger("pickup_today", tokens)

    async def _set(self, cap: str, value) -> None:
        try:
            await self.set_capability_value(cap, value)
        except Exception as e:
            self.log(f"set_capability_value({cap}) failed: {e}")

    async def _trigger(self, card_id: str, tokens: dict) -> None:
        try:
            card = self.homey.flow.get_trigger_card(card_id)
            await card.trigger(self, tokens, {})
        except Exception as e:
            self.log(f"Trigger '{card_id}' failed: {e}")


homey_export = SysavBinDevice
