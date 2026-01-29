from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Callable

try:
    import RPi.GPIO as GPIO
except ImportError as e:  # allow import on non-Pi for dev
    GPIO = None


@dataclass
class ButtonListener:
    pin: int
    pull: str
    debounce_ms: int
    on_press: Callable[[], None]

    def start(self) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available. Run on Raspberry Pi or install RPi.GPIO.")

        GPIO.setmode(GPIO.BCM)
        pud = GPIO.PUD_UP if self.pull == "up" else GPIO.PUD_DOWN
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

        # Edge depends on pull direction:
        edge = GPIO.FALLING if self.pull == "up" else GPIO.RISING

        last = 0.0

        def _cb(_channel: int) -> None:
            nonlocal last
            now = time.monotonic() * 1000
            if (now - last) < self.debounce_ms:
                return
            last = now
            self.on_press()

        GPIO.add_event_detect(self.pin, edge, callback=_cb, bouncetime=self.debounce_ms)

    def loop_forever(self) -> None:
        try:
            while True:
                time.sleep(1)
        finally:
            if GPIO is not None:
                GPIO.cleanup()
