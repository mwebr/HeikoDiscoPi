from __future__ import annotations
import argparse
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    GPIO = None


def cli() -> None:
    ap = argparse.ArgumentParser(description="GPIO digital read-out helper")
    ap.add_argument("--pin", type=int, required=True)
    ap.add_argument("--pull", choices=["up", "down", "none"], default="none")
    args = ap.parse_args()

    if GPIO is None:
        raise RuntimeError("RPi.GPIO not available.")

    GPIO.setmode(GPIO.BCM)
    pud = GPIO.PUD_UP if args.pull == "up" else GPIO.PUD_DOWN
    GPIO.setup(args.pin, GPIO.IN, pull_up_down=pud)

    try:
        while True:
            print(GPIO.input(args.pin))
            time.sleep(0.1)
    finally:
        GPIO.cleanup()
