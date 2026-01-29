from __future__ import annotations

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from typing import Literal


class GPIOConfig(BaseModel):
    button_pin: int = 17
    pull: Literal["up", "down"] = "up"
    debounce_ms: int = 80


class ZigbeeConfig(BaseModel):
    serial_port: str = "/dev/ttyUSB0"
    baudrate: int = 115200
    adapter: Literal["bellows", "znp", "deconz", "xbee"] = "znp"
    outlet_ieee: str  # "00:..:.."
    outlet_endpoint: int = 1


class AudioConfig(BaseModel):
    usb_autodetect: bool = True
    usb_mount_roots: list[str] = Field(default_factory=lambda: ["/media", "/mnt"])
    local_folders: list[str] = Field(default_factory=list)
    source_policy: Literal["random", "prefer_usb"] = "random"
    extensions: list[str] = Field(default_factory=lambda: [".mp3", ".wav", ".ogg", ".m4a", ".aac"])
    alsa_device: str = ""


class BehaviorConfig(BaseModel):
    press_during_playback: Literal["ignore", "restart", "stop"] = "ignore"


class AppConfig(BaseSettings):
    gpio: GPIOConfig
    zigbee: ZigbeeConfig
    audio: AudioConfig
    behavior: BehaviorConfig = BehaviorConfig()

    @classmethod
    def from_toml(cls, path: str) -> "AppConfig":
        from tomlkit import parse

        with open(path, "r", encoding="utf-8") as f:
            data = parse(f.read())
        return cls.model_validate(data)
