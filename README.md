# Heikodiscopi

**Heikodiscopi** is a Raspberry Pi “Disco Mode” trigger that listens to a wired emergency button on GPIO and, on press, turns on an IKEA Zigbee power outlet (“fuse”) via a Zigbee USB dongle and plays a random audio track until it ends. It supports USB-stick hot-plug (auto-mount + on-the-fly media discovery), local media folders, a single config file for GPIO/Zigbee/audio settings, boot-on-start via systemd, plus two debug utilities (GPIO digital readout + Zigbee scanner/tester). Built as a Python package and also as a `.deb`, with dependency management using **pyproject.toml + uv** and a GitHub Actions build pipeline. Licensed under **MIT**.

---

# Functionality

Disco Mode for Raspberry Pi:
- GPIO emergency button press triggers:
  - Zigbee IKEA outlet ("fuse") ON
  - plays a random audio file
  - outlet stays ON until playback ends
  - then outlet OFF
- USB stick support: auto-mount + discover music on the fly
- Config file for GPIO/Zigbee/audio paths
- Debug utilities:
  - GPIO digital readout tool
  - Zigbee scanner/tester tool
- Boot-on-start via systemd
- Packaged as Python package + .deb
- Dependency management: pyproject.toml + uv
- License: MIT

## Hardware
- Raspberry Pi (GPIO)
- Zigbee dongle (e.g. Sonoff ZBDongle, ConBee, etc.)
- IKEA Zigbee smart outlet
- Wired emergency button connected to a GPIO input + GND (with pull-up/down accordingly)
- Audio out (3.5mm jack, HDMI, USB DAC, etc.)

## Install (dev)
```bash
uv sync --dev
uv run heikodiscopi --config /etc/heikodiscopi/config.toml
````

## Install (system)

* Build wheel or .deb locally or get it from the package registry.
* Enable systemd service: `sudo systemctl enable --now heikodiscopi`

## Pairing Zigbee

Pair your IKEA outlet with the coordinator once, then set its IEEE / NWK address in config.
Use:

```bash
uv run heikodiscopi-zigbee --config ./config.toml scan
uv run heikodiscopi-zigbee --config ./config.toml test --on
```

## Config

See `config.example.toml` below (create your own).

```
[gpio]
button_pin = 17            # BCM numbering
pull = "up"                # "up" or "down"
debounce_ms = 80

[zigbee]
# Adapter backend depends on dongle + zigpy radio library.
# Example serial port:
serial_port = "/dev/ttyUSB0"
baudrate = 115200
# adapter: "bellows" | "znp" | "deconz" | "xbee"
adapter = "znp"

# Target outlet identifier:
# Prefer IEEE (EUI64) when possible.
outlet_ieee = "00:12:4b:00:2a:bc:de:f0"
outlet_endpoint = 1

[audio]
# If usb_autodetect=true, scan mounted removable media under these roots:
usb_autodetect = true
usb_mount_roots = ["/media", "/mnt"]

# Local fallback folders (can be empty):
local_folders = ["/home/pi/Music", "/opt/heikodiscopi/music"]

# When both USB + local available:
# "random" -> randomly pick a source each trigger
# "prefer_usb" -> use usb if present
source_policy = "random"

# Supported file extensions:
extensions = [".mp3", ".wav", ".ogg", ".m4a", ".aac", ".flac"]

# Optional: ALSA device name if you want to force output
alsa_device = ""

[behavior]
# When pressed during playback:
# "ignore" | "restart" | "stop"
press_during_playback = "ignore"
```

## Debian package

Clean build and install

```bash
sudo dpkg --remove --force-remove-reinstreq heikodiscopi || true
sudo dpkg --configure -a || true

sudo rm -rf debian/heikodiscopi debian/tmp .pybuild dist build debian/.debhelper/ debian/debhelper-build-stamp debian/files debian/heikodiscopi.postinst.debhelper debian/heikodiscopi.postrm.debhelper debian/heikodiscopi.prerm.debhelper debian/heikodiscopi.substvars

dpkg-buildpackage -us -uc -b

install -m 0644 ../heikodiscopi_*.deb /tmp/
sudo apt install /tmp/heikodiscopi_*.deb

sudo systemctl daemon-reload
sudo systemctl restart heikodiscopi.service
sudo systemctl status heikodiscopi.service
```


Troubleshooting / Service Logs

```bash
journalctl -u heikodiscopi.service -b -n 200 --no-pager
```


# ToDos:

- [ ] Set volume on system boot to 85% 
  ```bash
  wpctl set-volume -l 0.85 @DEFAULT_AUDIO_SINK@ 0.85
  ```
- [ ] Implement learning mode for zigbee database
- [ ] Implement pre-warm phase: emergency light before disco light
- [ ] Set correct config and values in Debian package
- [ ] Make system processes non-parallel (avoid double play)