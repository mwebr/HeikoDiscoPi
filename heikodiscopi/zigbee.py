from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import zigpy.config
import zigpy.types as t

# Map config adapter -> python module that provides ControllerApplication
ADAPTER_MODULE = {
    "znp": "zigpy_znp.zigbee.application",
    "bellows": "bellows.zigbee.application",
    "deconz": "zigpy_deconz.zigbee.application",
    "xbee": "zigpy_xbee.zigbee.application",
}


@dataclass(frozen=True)
class ZigbeeOutlet:
    ieee: str
    endpoint: int = 1


class ZigbeeController:
    def __init__(self, *, adapter: str, serial_port: str, baudrate: int) -> None:
        self.adapter = adapter
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.app: Optional[object] = None  # concrete ControllerApplication type varies

    async def start(self) -> None:
        mod_path = ADAPTER_MODULE.get(self.adapter)
        if not mod_path:
            raise ValueError(f"Unsupported adapter '{self.adapter}'. Choose one of {sorted(ADAPTER_MODULE)}")

        # Dynamically import the correct adapter ControllerApplication
        module = __import__(mod_path, fromlist=["ControllerApplication"])
        AppCls = getattr(module, "ControllerApplication")

        cfg = {
            zigpy.config.CONF_DEVICE: {
                zigpy.config.CONF_DEVICE_PATH: self.serial_port,
                zigpy.config.CONF_DEVICE_BAUDRATE: self.baudrate,
            },
            zigpy.config.CONF_DATABASE: "zigbee.db",
        }

        # Adapter-specific ControllerApplication.new(...)
        # NOTE: use auto_form=True here; don't call startup() separately (avoids double-connect on some radios)
        self.app = await AppCls.new(cfg, auto_form=True)

    async def stop(self) -> None:
        if self.app is not None:
            await self.app.shutdown()
            self.app = None

    def _require_app(self):
        if self.app is None:
            raise RuntimeError("ZigbeeController not started.")
        return self.app

    @staticmethod
    def _to_eui64(ieee: str) -> t.EUI64:
        # zigpy expects hex without colons; EUI64.convert handles multiple formats too
        return t.EUI64.convert(ieee.replace(":", "").replace("-", ""))

    async def permit_join(self, seconds: int = 180) -> None:
        """
        Allow new devices to join the network for `seconds`.

        Some radios expose permit_ncp(); others expose permit().
        """
        app = self._require_app()
        seconds_u8 = max(0, min(int(seconds), 254))

        if hasattr(app, "permit"):
            await app.permit(seconds)

        if hasattr(app, "permit_ncp"):
            await app.permit_ncp(seconds)

    async def set_onoff(self, outlet: ZigbeeOutlet, on: bool) -> None:
        app = self._require_app()

        ieee = self._to_eui64(outlet.ieee)
        dev = app.devices.get(ieee)
        if dev is None:
            raise RuntimeError(
                f"Outlet not found in zigbee.db: {outlet.ieee}. "
                "Run heikodiscopi-zigbee scan, pair device, or check outlet_ieee."
            )

        ep = dev.endpoints.get(outlet.endpoint)
        if ep is None:
            raise RuntimeError(f"Endpoint {outlet.endpoint} missing on device {outlet.ieee}")

        cluster = getattr(ep, "on_off", None)
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
            out.append(f"{ieee}  nwk={getattr(dev, 'nwk', None)}  manuf={dev.manufacturer}  model={dev.model}")
        return sorted(out)
