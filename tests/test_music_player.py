#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pytest

from bwflasher.music_player import PLAYLIST, format_track_label, wrap_index


def test_wrap_index_forward():
    assert wrap_index(0, 4) == 0
    assert wrap_index(3, 4) == 3
    assert wrap_index(4, 4) == 0
    assert wrap_index(5, 4) == 1


def test_wrap_index_backward():
    assert wrap_index(-1, 4) == 3
    assert wrap_index(-2, 4) == 2


def test_wrap_index_empty_playlist():
    assert wrap_index(0, 0) == 0
    assert wrap_index(5, 0) == 0


def test_format_track_label():
    playlist = [("Alpha", "a.mp3"), ("Beta", "b.mp3")]
    assert format_track_label(0, playlist) == "Track 1/2: Alpha"
    assert format_track_label(1, playlist) == "Track 2/2: Beta"
    assert format_track_label(2, playlist) == "Track 1/2: Alpha"


def test_format_track_label_empty():
    assert format_track_label(0, []) == "No tracks"


def test_playlist_has_expected_tracks():
    titles = [title for title, _ in PLAYLIST]
    assert titles == ["Original", "Happy Adventure", "Chippey"]
