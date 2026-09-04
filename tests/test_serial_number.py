#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.

import pytest

from bwflasher.serial_number import (
    SERIAL_NUMBER_LENGTH,
    build_serial_packet,
    calculate_crc16,
    parse_response,
    send_serial_command,
    validate_serial_number,
)

SAMPLE_SN = "0539370000000ABCDEF"
SAMPLE_PACKET_HEX = (
    "5a 12 97 14 30 30 35 33 39 33 37 30 30 30 30 30 30 30 41 42 43 44 45 46 e3 b8"
)


def test_validate_serial_number_accepts_19_ascii():
    assert validate_serial_number(SAMPLE_SN) == SAMPLE_SN


@pytest.mark.parametrize(
    "value",
    [
        "",
        "short",
        "x" * (SERIAL_NUMBER_LENGTH + 1),
        "0539370000000ABCDÉ",  # non-ASCII
    ],
)
def test_validate_serial_number_rejects_invalid(value):
    with pytest.raises(ValueError):
        validate_serial_number(value)


def test_build_serial_packet_known_vector():
    packet = build_serial_packet(SAMPLE_SN)
    assert packet.hex(" ") == SAMPLE_PACKET_HEX
    assert calculate_crc16(packet[:-2]) == 0xE3B8


def test_parse_response_success():
    packet = build_serial_packet(SAMPLE_SN)
    success, serial_number, message = parse_response(packet)
    assert success is True
    assert serial_number == SAMPLE_SN
    assert message == "OK"


def test_parse_response_crc_mismatch():
    packet = bytearray(build_serial_packet(SAMPLE_SN))
    packet[-1] ^= 0xFF
    success, serial_number, message = parse_response(bytes(packet))
    assert success is False
    assert serial_number == SAMPLE_SN
    assert "CRC mismatch" in message


def test_send_serial_command_simulation():
    logs = []
    success, serial_number, message = send_serial_command(
        port="/dev/null",
        serial_number=SAMPLE_SN,
        simulation=True,
        debug_callback=logs.append,
    )
    assert success is True
    assert serial_number == SAMPLE_SN
    assert "simulated" in message
    assert any("[SIM]" in line for line in logs)
    assert any("[TX]" in line for line in logs)
    assert any("[RX]" in line for line in logs)
