from __future__ import annotations

import argparse
import asyncio

from ..config import AppConfig
from ..zigbee import ZigbeeController, ZigbeeOutlet


async def _scan(cfg: AppConfig) -> None:
    zb = ZigbeeController(
        adapter=cfg.zigbee.adapter,
        serial_port=cfg.zigbee.serial_port,
        baudrate=cfg.zigbee.baudrate,
    )
    await zb.start()
    try:
        for line in await zb.scan_devices():
            print(line)
    finally:
        await zb.stop()


async def _test(cfg: AppConfig, on: bool) -> None:
    zb = ZigbeeController(
        adapter=cfg.zigbee.adapter,
        serial_port=cfg.zigbee.serial_port,
        baudrate=cfg.zigbee.baudrate,
    )
    outlet = ZigbeeOutlet(cfg.zigbee.outlet_ieee, cfg.zigbee.outlet_endpoint)
    await zb.start()
    try:
        await zb.set_onoff(outlet, on)
    finally:
        await zb.stop()


async def _permit(cfg: AppConfig, seconds: int) -> None:
    zb = ZigbeeController(
        adapter=cfg.zigbee.adapter,
        serial_port=cfg.zigbee.serial_port,
        baudrate=cfg.zigbee.baudrate,
    )
    await zb.start()
    try:
        await zb.permit_join(seconds)
        print(f"Permit join enabled for {seconds}s")

        seen: set[str] = set()
        # print existing devices once
        for line in await zb.scan_devices():
            print(line)
            seen.add(line)

        # poll and print new ones during permit window
        for _ in range(max(1, seconds // 2)):
            await asyncio.sleep(2)
            lines = await zb.scan_devices()
            for line in lines:
                if line not in seen:
                    print("NEW:", line)
                    seen.add(line)
    finally:
        await zb.stop()


def cli() -> None:
    ap = argparse.ArgumentParser(description="Zigbee scan/test helper")
    ap.add_argument("--config", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("scan")

    t = sub.add_parser("test")
    t.add_argument("--on", action="store_true")
    t.add_argument("--off", action="store_true")

    p = sub.add_parser("permit")
    p.add_argument("--seconds", type=int, default=180)

    args = ap.parse_args()
    cfg = AppConfig.from_toml(args.config)

    if args.cmd == "scan":
        asyncio.run(_scan(cfg))
    elif args.cmd == "test":
        if args.on == args.off:
            raise SystemExit("Specify exactly one: --on or --off")
        asyncio.run(_test(cfg, on=args.on))
    elif args.cmd == "permit":
        asyncio.run(_permit(cfg, args.seconds))
