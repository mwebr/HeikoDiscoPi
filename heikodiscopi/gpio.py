from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


@dataclass
class ButtonListener:
    pin: int
    pull: str  # "up" | "down" | "none"
    debounce_ms: int
    on_press: Callable[[], None]

    def start(self) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available.")

        GPIO.setmode(GPIO.BCM)

        if self.pull == "up":
            pud = GPIO.PUD_UP
        elif self.pull == "down":
            pud = GPIO.PUD_DOWN
        else:
            pud = GPIO.PUD_OFF

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=pud)

    def loop_forever(self) -> None:
        if GPIO is None:
            raise RuntimeError("RPi.GPIO not available.")

        # Determine "pressed" level based on pull style
        # pull-up wiring => pressed pulls to GND => 0 means pressed
        pressed_level = 1 if self.pull == "down" else 0

        last_state = GPIO.input(self.pin)
        last_press_t = 0.0

        poll_s = 0.01  # 10ms
        debounce_s = max(0.0, self.debounce_ms / 1000.0)

        try:
            while True:
                state = GPIO.input(self.pin)
                # detect transition to pressed
                if state == pressed_level and last_state != pressed_level:
                    now = time.monotonic()
                    if now - last_press_t >= debounce_s:
                        last_press_t = now
                        self.on_press()
                last_state = state
                time.sleep(poll_s)
        finally:
            GPIO.cleanup(self.pin)
