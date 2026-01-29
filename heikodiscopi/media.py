from __future__ import annotations

import logging
import os
import random
from dataclasses import dataclass
from pathlib import Path

import psutil

log = logging.getLogger(__name__)


@dataclass
class MediaLibrary:
    usb_autodetect: bool
    usb_mount_roots: list[str]
    local_folders: list[str]
    extensions: list[str]
    source_policy: str  # "random" | "prefer_usb"

    def _mounted_paths(self) -> list[Path]:
        mounts: list[Path] = []
        for p in psutil.disk_partitions(all=False):
            m = Path(p.mountpoint)
            if any(str(m).startswith(root.rstrip("/") + "/") or str(m) == root for root in self.usb_mount_roots):
                mounts.append(m)
        return mounts

    def _scan_folder(self, folder: Path) -> list[Path]:
        folder = folder.expanduser()

        # Normalize extensions: accept ".mp3" as well as "mp3"
        exts = {e.lower().strip() for e in self.extensions}
        exts = {e if e.startswith(".") else f".{e}" for e in exts}

        results: list[Path] = []
        if not folder.exists():
            return results

        try:
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    p = Path(root) / f
                    if p.suffix.lower() in exts:
                        results.append(p)
        except PermissionError as e:
            log.error("PermissionError scanning %s: %s", folder, e)

        return results

    def list_tracks(self) -> list[Path]:
        log.info("Media config: usb_autodetect=%s source_policy=%s", self.usb_autodetect, self.source_policy)
        log.info("Media config: usb_mount_roots=%s", self.usb_mount_roots)
        log.info("Media config: local_folders=%s", self.local_folders)
        log.info("Media config: extensions=%s", self.extensions)

        tracks_usb: list[Path] = []
        if self.usb_autodetect:
            mounts = self._mounted_paths()
            log.info("Detected mounts under roots: %s", mounts)
            for m in mounts:
                found = self._scan_folder(m)
                log.info("USB scan %s -> %d tracks", m, len(found))
                tracks_usb += found

        tracks_local: list[Path] = []
        for lf in self.local_folders:
            p = Path(str(lf)).expanduser()
            log.info("Scanning local folder: %s (exists=%s)", p, p.exists())
            found = self._scan_folder(p)
            log.info("Local scan %s -> %d tracks", p, len(found))
            tracks_local += found

        if tracks_usb and tracks_local:
            if self.source_policy == "prefer_usb":
                return tracks_usb
            # random policy => randomly pick a source per call
            return tracks_usb if random.choice([True, False]) else tracks_local

        return tracks_usb or tracks_local

    def choose_random_track(self) -> Path:
        tracks = self.list_tracks()
        if not tracks:
            raise RuntimeError("No audio tracks found (USB/local).")
        return random.choice(tracks)
