from __future__ import annotations

import argparse
import asyncio
import logging
import threading
import time
from typing import Optional

from .audio import AudioPlayer
from .config import AppConfig
from .gpio import ButtonListener
from .media import MediaLibrary
from .zigbee import ZigbeeController, ZigbeeOutlet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DiscoApp:
    def __init__(self, cfg: AppConfig) -> None:
        self.cfg = cfg

        self.zb = ZigbeeController(
            adapter=cfg.zigbee.adapter,
            serial_port=cfg.zigbee.serial_port,
            baudrate=cfg.zigbee.baudrate,
        )
        self.outlet = ZigbeeOutlet(cfg.zigbee.outlet_ieee, cfg.zigbee.outlet_endpoint)

        # mpv IPC-backed AudioPlayer (Option A)
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

        # Zigpy binds to the event loop it was started on
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        await self.zb.start()

    async def stop(self) -> None:
        await self.zb.stop()

    def _zigbee_call(self, coro) -> None:
        if self._loop is None:
            raise RuntimeError("Async loop not initialized (call start() first).")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        fut.result()

    def on_button_press(self) -> None:
        with self._lock:
            if self._playing and self.cfg.behavior.press_during_playback == "ignore":
                return
            if self._playing and self.cfg.behavior.press_during_playback == "stop":
                self.player.stop()
                return
            if self._playing and self.cfg.behavior.press_during_playback == "restart":
                self.player.stop()

            threading.Thread(target=self._run_disco_once_thread, daemon=True).start()

    def _run_disco_once_thread(self) -> None:
        with self._lock:
            self._playing = True

        playback_thread: Optional[threading.Thread] = None

        try:
            track = self.library.choose_random_track()
            logger.info("Selected track: %s", track)

            # Start playback in its own thread so we can wait for "started" and then toggle Zigbee ON
            exc_holder: list[BaseException] = []

            def _play() -> None:
                try:
                    self.player.play_blocking(str(track))
                except BaseException as e:
                    exc_holder.append(e)

            playback_thread = threading.Thread(target=_play, daemon=True)
            playback_thread.start()

            # Wait until audio actually starts (mpv IPC) before turning the outlet ON
            started = self.player.wait_until_started(timeout_s=5.0)
            if started:
                logger.info("Audio started; switching outlet ON")
            else:
                logger.warning("Audio start not confirmed within timeout; switching outlet ON anyway")

            self._zigbee_call(self.zb.set_onoff(self.outlet, True))

            # Wait for playback to finish
            playback_thread.join()

            # If playback thread failed, surface it
            if exc_holder:
                raise exc_holder[0]

        except Exception as e:
            logger.error("Disco run failed: %s", e, exc_info=True)

        finally:
            try:
                self._zigbee_call(self.zb.set_onoff(self.outlet, False))
            except Exception as e:
                logger.error("Zigbee OFF failed: %s", e, exc_info=True)

            with self._lock:
                self._playing = False


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

        # If the ButtonListener requires a loop (polling implementation),
        # run it in a background thread so we don't block asyncio.
        if hasattr(bl, "loop_forever") and callable(getattr(bl, "loop_forever")):
            threading.Thread(target=bl.loop_forever, daemon=True).start()

        logger.info("READY: waiting for button press on BCM pin %s", cfg.gpio.button_pin)

        # Keep asyncio loop alive (do NOT block with a sync while True here)
        await asyncio.Event().wait()

    try:
        asyncio.run(_runner())
    except KeyboardInterrupt:
        pass
