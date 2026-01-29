from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class AudioPlayer:
    alsa_device: str = ""  # optional, e.g. "hw:0,0"
    _proc: subprocess.Popen | None = None

    def __post_init__(self) -> None:
        if shutil.which("ffplay") is None:
            raise RuntimeError("ffplay not found. Install with: sudo apt-get install -y ffmpeg")

    def play_blocking(self, file_path: str) -> None:
        p = Path(file_path)
        if not p.exists():
            raise RuntimeError(f"Audio file does not exist: {p}")

        # ffplay uses SDL/ALSA; on headless this is usually fine.
        # -nodisp: no window
        # -autoexit: exit when done
        # -loglevel error: less noise
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(p)]

        env = None
        if self.alsa_device:
            # One common way to force ALSA device is via ALSA env vars
            # (works depending on system config)
            env = dict(**{k: v for k, v in (subprocess.os.environ or {}).items()})
            env["ALSA_DEVICE"] = self.alsa_device

        log.info("Starting playback (ffplay): %s", p)
        self._proc = subprocess.Popen(cmd, env=env)
        rc = self._proc.wait()
        self._proc = None

        if rc != 0:
            raise RuntimeError(f"ffplay exited with code {rc} for {p}")

        log.info("Playback finished: %s", p)

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None
