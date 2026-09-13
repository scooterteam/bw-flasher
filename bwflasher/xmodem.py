#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher - shared XMODEM-style framing (Brightway DFU)
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

import binascii

CHUNK_SIZE = 0x80
FRAME_LEN = CHUNK_SIZE + 5  # SOH + seq + complement + payload + CRC16
ACK = 0x06
NAK = 0x15
EOT = b"\x04"


def crc16_xmodem(data: bytes) -> int:
    return binascii.crc_hqx(data, 0)


def pad_chunk(payload: bytes, size: int = CHUNK_SIZE, pad: int = 0xFF) -> bytes:
    if len(payload) > size:
        raise ValueError(f"payload longer than {size}")
    return bytes(payload) + bytes([pad] * (size - len(payload)))


def build_frame(seq: int, payload: bytes, *, chunk_size: int = CHUNK_SIZE) -> bytes:
    """Build ``01 seq seq_complement payload[128] crc16_be`` frame."""
    if not (1 <= seq <= 0xFF):
        raise ValueError(f"seq out of range: {seq}")
    body = pad_chunk(payload, chunk_size)
    crc = crc16_xmodem(body)
    return bytes([0x01, seq, seq ^ 0xFF]) + body + bytes([(crc >> 8) & 0xFF, crc & 0xFF])
