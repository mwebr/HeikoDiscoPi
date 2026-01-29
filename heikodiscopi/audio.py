from __future__ import annotations

import json
import logging
import os
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class AudioPlayer:
    alsa_device: str = ""  # optional, e.g. "plughw:1,0"
    _proc: subprocess.Popen | None = None
    _sock_path: str | None = None

    def _send(self, msg: dict) -> dict:
        if not self._sock_path:
            raise RuntimeError("mpv socket not initialized")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(self._sock_path)
            s.sendall((json.dumps(msg) + "\n").encode("utf-8"))
            data = b""
            while not data.endswith(b"\n"):
                chunk = s.recv(4096)
                if not chunk:
                    break
                data += chunk
        if not data:
            return {}
        return json.loads(data.decode("utf-8"))

    def _get_prop(self, name: str):
        resp = self._send({"command": ["get_property", name]})
        return resp.get("data")

    def play_blocking(self, file_path: str) -> None:
        p = Path(file_path)
        if not p.exists():
            raise RuntimeError(f"Audio file does not exist: {p}")

        # Create a unique IPC socket path
        tmpdir = tempfile.mkdtemp(prefix="heikodiscopi-mpv-")
        self._sock_path = os.path.join(tmpdir, "mpv.sock")

        cmd = [
            "mpv",
            "--no-video",
            "--really-quiet",
            "--idle=no",
            "--force-window=no",
            f"--input-ipc-server={self._sock_path}",
            "--audio-display=no",
            str(p),
        ]

        if self.alsa_device:
            # Force ALSA device (optional). mpv uses ao=alsa on Linux typically.
            cmd.insert(1, "--ao=alsa")
            cmd.insert(2, f"--audio-device=alsa/{self.alsa_device}")

        log.info("Starting playback (mpv): %s", p)
        self._proc = subprocess.Popen(cmd)

        try:
            # Wait until playback has actually started:
            # playback-time becomes > 0 once audio starts
            started = False
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline:
                if self._proc.poll() is not None:
                    raise RuntimeError(f"mpv exited early with code {self._proc.returncode}")
                try:
                    t = self._get_prop("playback-time")
                    if isinstance(t, (int, float)) and t > 0.0:
                        started = True
                        break
                except Exception:
                    pass
                time.sleep(0.05)

            if not started:
                log.warning("Playback did not report playback-time > 0 within 5s; continuing anyway.")

            # Block until finished
            rc = self._proc.wait()
            if rc != 0:
                raise RuntimeError(f"mpv exited with code {rc} for {p}")

        finally:
            self._proc = None
            # best-effort cleanup; socket dir can be left if crash, not critical
            self._sock_path = None

    def wait_until_started(self, timeout_s: float = 5.0) -> bool:
        # Used by main to align Zigbee ON with playback start
        if not self._proc or not self._sock_path:
            return False
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                return False
            try:
                t = self._get_prop("playback-time")
                if isinstance(t, (int, float)) and t > 0.0:
                    return True
            except Exception:
                pass
            time.sleep(0.05)
        return False

    def stop(self) -> None:
        if self._proc and self._proc.poll() is None:
            try:
                self._send({"command": ["quit"]})
            except Exception:
                self._proc.terminate()
            try:
                self._proc.wait(timeout=2)
            except Exception:
                self._proc.kill()
            finally:
                self._proc = None
                self._sock_path = None
