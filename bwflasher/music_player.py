#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# BW Flasher - Chiptune music player
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

import os
import sys

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

PLAYLIST = [
    ("Original", "chiptune.mp3"),
]


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, "resources", relative_path)


def wrap_index(index, length):
    """Return index wrapped to playlist bounds."""
    if length <= 0:
        return 0
    return index % length


def format_track_label(index, playlist=None):
    """Format playlist position for display."""
    tracks = playlist if playlist is not None else PLAYLIST
    if not tracks:
        return "No tracks"
    index = wrap_index(index, len(tracks))
    title, _ = tracks[index]
    return f"Track {index + 1}/{len(tracks)}: {title}"


class ChiptunePlayer(QObject):
    """Playlist-aware wrapper around QMediaPlayer."""

    track_changed = Signal(int, str)
    playback_state_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._index = 0
        self._available = False

        try:
            self.player = QMediaPlayer(self)
            self.audio_output = QAudioOutput(self)
            self.player.setAudioOutput(self.audio_output)
            self.player.mediaStatusChanged.connect(self._on_media_status_changed)
            self.player.playbackStateChanged.connect(self._on_playback_state_changed)
            self._available = True
        except Exception:
            self.player = None
            self.audio_output = None

    @property
    def available(self):
        return self._available and bool(PLAYLIST)

    @property
    def current_index(self):
        return self._index

    @property
    def is_playing(self):
        if not self.player:
            return False
        return self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState

    def track_label(self):
        return format_track_label(self._index)

    def _track_path(self, index):
        _, relative_path = PLAYLIST[wrap_index(index, len(PLAYLIST))]
        return resource_path(relative_path)

    def _load_track(self, index, autoplay=False):
        if not self.available:
            return

        self._index = wrap_index(index, len(PLAYLIST))
        title, _ = PLAYLIST[self._index]
        path = self._track_path(self._index)

        if not os.path.exists(path):
            return

        self.player.setSource(QUrl.fromLocalFile(path))
        self.track_changed.emit(self._index, title)

        if autoplay:
            self.player.play()

    def start(self):
        """Load first track and begin playback."""
        if not self.available:
            return
        self._load_track(0, autoplay=True)

    def toggle_play_stop(self):
        if not self.available:
            return

        if self.is_playing:
            self.player.stop()
        elif self.player.mediaStatus() == QMediaPlayer.MediaStatus.NoMedia:
            self._load_track(self._index, autoplay=True)
        else:
            self.player.play()

    def stop(self):
        if not self.available:
            return
        self.player.stop()

    def next_track(self):
        if not self.available:
            return
        playing = self.is_playing
        self._load_track(self._index + 1, autoplay=playing)

    def prev_track(self):
        if not self.available:
            return
        playing = self.is_playing
        self._load_track(self._index - 1, autoplay=playing)

    def _on_media_status_changed(self, status):
        if not self.available:
            return
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._load_track(self._index + 1, autoplay=True)

    def _on_playback_state_changed(self, state):
        self.playback_state_changed.emit(
            state == QMediaPlayer.PlaybackState.PlayingState
        )
