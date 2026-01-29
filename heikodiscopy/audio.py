from __future__ import annotations

import time
from dataclasses import dataclass
import vlc


@dataclass
class AudioPlayer:
    alsa_device: str = ""

    def __post_init__(self) -> None:
        args = []
        if self.alsa_device:
            # Force ALSA output (optional)
            args += ["--aout=alsa", f"--alsa-audio-device={self.alsa_device}"]
        self._instance = vlc.Instance(args)
        self._player = self._instance.media_player_new()

    def play_blocking(self, file_path: str) -> None:
        media = self._instance.media_new(file_path)
        self._player.set_media(media)
        self._player.play()

        # Wait for playback to actually start
        for _ in range(50):
            st = self._player.get_state()
            if st in (vlc.State.Playing, vlc.State.Paused, vlc.State.Ended, vlc.State.Error):
                break
            time.sleep(0.1)

        # Block until finished
        while True:
            st = self._player.get_state()
            if st in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
                break
            time.sleep(0.25)

    def stop(self) -> None:
        self._player.stop()
