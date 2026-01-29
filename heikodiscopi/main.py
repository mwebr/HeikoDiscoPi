from __future__ import annotations

import argparse
import asyncio
import threading
import logging

from .config import AppConfig
from .gpio import ButtonListener
from .zigbee import ZigbeeController, ZigbeeOutlet
from .audio import AudioPlayer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .media import MediaLibrary


class DiscoApp:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg
        self.zb = ZigbeeController(
            adapter=cfg.zigbee.adapter,
            serial_port=cfg.zigbee.serial_port,
            baudrate=cfg.zigbee.baudrate,
        )
        self.outlet = ZigbeeOutlet(cfg.zigbee.outlet_ieee, cfg.zigbee.outlet_endpoint)
        self.player = AudioPlayer(alsa_device=cfg.audio.alsa_device)
        self.library = MediaLibrary(
            usb_autodetect=cfg.audio.usb_autodetect,
            usb_mount_roots=cfg.audio.usb_mount_roots,
            local_folders=cfg.audio.local_folders,
            extensions=cfg.audio.extensions,
            source_policy=cfg.audio.source_policy,
        )

        self._lock = threading.Lock()
        self._playing = False

    async def start(self) -> None:
        await self.zb.start()

    async def stop(self) -> None:
        await self.zb.stop()

    def on_button_press(self) -> None:
        with self._lock:
            if self._playing and self.cfg.behavior.press_during_playback == "ignore":
                return
            if self._playing and self.cfg.behavior.press_during_playback == "stop":
                self.player.stop()
                return
            # restart or not playing:
            if self._playing and self.cfg.behavior.press_during_playback == "restart":
                self.player.stop()

            t = threading.Thread(target=self._run_disco_once_thread, daemon=True)
            t.start()

    def _run_disco_once_thread(self) -> None:
        with self._lock:
            self._playing = True
        try:
            track = self.library.choose_random_track()
            asyncio.run(self._zigbee_on())
            self.player.play_blocking(str(track))
        except Exception as e:
            logger.error(f"ERROR: {e}")
        finally:
            try:
                asyncio.run(self._zigbee_off())
            except Exception as e:
                logger.error(f"Zigbee OFF failed: {e}")
            with self._lock:
                self._playing = False

    async def _zigbee_on(self) -> None:
        await self.zb.set_onoff(self.outlet, True)

    async def _zigbee_off(self) -> None:
        await self.zb.set_onoff(self.outlet, False)


def cli() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to config TOML")
    args = ap.parse_args()

    cfg = AppConfig.from_toml(args.config)
    app = DiscoApp(cfg)

    async def _runner() -> None:
        await app.start()

        bl = ButtonListener(
            pin=cfg.gpio.button_pin,
            pull=cfg.gpio.pull,
            debounce_ms=cfg.gpio.debounce_ms,
            on_press=app.on_button_press,
        )
        bl.start()
        bl.loop_forever()

    try:
        asyncio.run(_runner())
    except KeyboardInterrupt:
        pass
