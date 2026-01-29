from __future__ import annotations

import os
import random
from dataclasses import dataclass
from pathlib import Path

import psutil


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
        exts = {e.lower() for e in self.extensions}
        results: list[Path] = []
        if not folder.exists():
            return results
        for root, _dirs, files in os.walk(folder):
            for f in files:
                p = Path(root) / f
                if p.suffix.lower() in exts:
                    results.append(p)
        return results

    def list_tracks(self) -> list[Path]:
        tracks_usb: list[Path] = []
        if self.usb_autodetect:
            for m in self._mounted_paths():
                tracks_usb += self._scan_folder(m)

        tracks_local: list[Path] = []
        for lf in self.local_folders:
            tracks_local += self._scan_folder(Path(lf))

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
