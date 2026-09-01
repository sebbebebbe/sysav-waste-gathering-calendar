import re

from homey.driver import Driver


def _slug(value: str) -> str:
    value = (value or "").strip().lower()
    value = value.replace("å", "a").replace("ä", "a").replace("ö", "o")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


class SysavBinDriver(Driver):

    async def on_init(self) -> None:
        await super().on_init()
        self.log("SysavBinDriver init")

    async def on_pair(self, session) -> None:
        context = {
            "street_name": "",
            "street_number": "",
            "city": "",
            "schedule": [],
        }

        async def on_address(data: dict) -> bool:
            self.log(f"pair on_address received: {data!r}")
            street_name = str(data.get("street_name", "")).strip()
            street_number = str(data.get("street_number", "")).strip()
            city = str(data.get("city", "")).strip()
            if not street_name or not street_number or not city:
                raise Exception("Fyll i gata, nummer och ort.")

            self.log(f"pair fetching schedule for {street_name} {street_number}, {city}")
            schedule = await self.homey.app.fetch_schedule(
                street_name, street_number, city, force=True
            )
            self.log(f"pair got {len(schedule) if schedule else 0} schedule entries")
            if not schedule:
                raise Exception("Sysav hittade inga kärl för adressen. Kontrollera på sysav.se.")

            context["street_name"] = street_name
            context["street_number"] = street_number
            context["city"] = city
            context["schedule"] = schedule
            return True

        async def on_list_devices(data: dict = None) -> list:
            self.log(f"pair on_list_devices called (schedule entries: {len(context['schedule'])})")
            schedule = context["schedule"]
            if not schedule:
                raise Exception("Sysav hittade inga kärl för adressen. Kontrollera på sysav.se.")

            devices = []
            for entry in schedule:
                waste_type = entry.get("wasteType") or entry.get("WasteType")
                if not waste_type:
                    continue
                dev_id = "_".join([
                    _slug(context["street_name"]),
                    _slug(context["street_number"]),
                    _slug(context["city"]),
                    _slug(waste_type),
                ])
                devices.append({
                    "name": f"{waste_type} – {context['street_name']} {context['street_number']}",
                    "data": {"id": dev_id},
                    "settings": {
                        "street_name": context["street_name"],
                        "street_number": context["street_number"],
                        "city": context["city"],
                        "waste_type": waste_type,
                    },
                })
            return devices

        session.set_handler("address", on_address)
        session.set_handler("list_devices", on_list_devices)


homey_export = SysavBinDriver
