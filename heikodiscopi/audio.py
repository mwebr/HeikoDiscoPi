from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class AudioPlayer:
    alsa_device: str = ""  # prefer "plughw:1,0" if you must specify
    warmup_wav: str = ""   # optional path to a short wav file
    _proc: subprocess.Popen | None = None

    def __post_init__(self) -> None:
        if shutil.which("ffplay") is None:
            raise RuntimeError("ffplay not found. Install with: sudo apt-get install -y ffmpeg")

        # Optional warmup (reduces first-play latency)
        if self.warmup_wav:
            self.warmup()

    def warmup(self) -> None:
        p = Path(self.warmup_wav)
        if not p.exists():
            return
        # aplay warmup is very lightweight; ignore errors
        if shutil.which("aplay"):
            subprocess.run(["aplay", "-q", str(p)], check=False)
        else:
            # fallback: quick ffplay warmup
            subprocess.run(
                ["ffplay", "-nodisp", "-autoexit", "-vn", "-loglevel", "error", str(p)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def play_blocking(self, file_path: str) -> None:
        p = Path(file_path)
        if not p.exists():
            raise RuntimeError(f"Audio file does not exist: {p}")

        cmd = [
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-vn",
            "-hide_banner",
            "-nostats",
            "-loglevel",
            "error",
            "-probesize",
            "32k",
            "-analyzeduration",
            "0",
            "-sync",
            "audio",
            str(p),
        ]

        env = dict(os.environ)
        env["SDL_AUDIODRIVER"] = "alsa"
        if self.alsa_device:
            # Not all builds honor this, but it's more common than ALSA_DEVICE.
            env["AUDIODEV"] = self.alsa_device

        log.info("Starting playback (ffplay): %s", p)
        self._proc = subprocess.Popen(cmd, env=env)
        rc = self._proc.wait()
        self._proc = None

        if rc != 0:
            raise RuntimeError(f"ffplay exited with code {rc} for {p}")

        log.info("Playback finished: %s", p)

    def stop(self) -> None:
        proc = self._proc
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:
                proc.kill()
                try:
                    proc.wait(timeout=2)
                except Exception:
                    pass
            finally:
                self._proc = None