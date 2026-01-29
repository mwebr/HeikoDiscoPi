from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import zigpy.application
import zigpy.config
import zigpy.types as t


ADAPTER_TO_RADIO = {
    "bellows": "bellows",
    "znp": "znp",
    "deconz": "deconz",
    "xbee": "xbee",
}


@dataclass
class ZigbeeOutlet:
    ieee: str
    endpoint: int = 1


class ZigbeeController:
    def __init__(self, *, adapter: str, serial_port: str, baudrate: int) -> None:
        self.adapter = adapter
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.app: Optional[zigpy.application.ControllerApplication] = None

    async def start(self) -> None:
        cfg = {
            zigpy.config.CONF_DEVICE: {
                zigpy.config.CONF_DEVICE_PATH: self.serial_port,
                zigpy.config.CONF_DEVICE_BAUDRATE: self.baudrate,
            },
            zigpy.config.CONF_DATABASE: "zigbee.db",
            zigpy.config.CONF_NWK_CHANNEL: 15,
        }

        radio_lib = ADAPTER_TO_RADIO[self.adapter]
        app_cls = zigpy.application.ControllerApplication
        self.app = await app_cls.new(radio_lib, cfg)
        await self.app.startup(auto_form=True)

    async def stop(self) -> None:
        if self.app is not None:
            await self.app.shutdown()
            self.app = None

    def _require_app(self) -> zigpy.application.ControllerApplication:
        if self.app is None:
            raise RuntimeError("ZigbeeController not started.")
        return self.app

    async def set_onoff(self, outlet: ZigbeeOutlet, on: bool) -> None:
        app = self._require_app()
        ieee = t.EUI64.convert(outlet.ieee.replace(":", ""))
        dev = app.devices.get(ieee)
        if dev is None:
            raise RuntimeError(f"Outlet not found in zigbee.db: {outlet.ieee}")

        ep = dev.endpoints.get(outlet.endpoint)
        if ep is None:
            raise RuntimeError(f"Endpoint {outlet.endpoint} missing on device {outlet.ieee}")

        cluster = ep.on_off
        if cluster is None:
            raise RuntimeError("OnOff cluster not available on that endpoint.")

        if on:
            await cluster.on()
        else:
            await cluster.off()

    async def scan_devices(self) -> list[str]:
        app = self._require_app()
        out: list[str] = []
        for ieee, dev in app.devices.items():
            out.append(f"{ieee}  nwk={dev.nwk}  manuf={dev.manufacturer}  model={dev.model}")
        return sorted(out)
