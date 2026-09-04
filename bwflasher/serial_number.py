#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher - LEQI Scooter Serial Number
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

"""
Set the scooter product serial number on LEQI scooters.

Command 0x97 is handled by the dashboard BLE firmware (RTL8762C), not the motor
controller. The value is the scooter serial (exposed via Xiaomi MIoT); it is
persisted in BLE NVM. Brightway and Ninebot do not support this protocol.

Protocol (19200 8N1):
  TX/RX: [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN...] [CRC_H] [CRC_L]
"""

from __future__ import annotations

import serial
import serial.tools.list_ports
import time
from typing import Callable, Optional, Tuple

SERIAL_NUMBER_LENGTH = 19
DEFAULT_BAUDRATE = 19200
LogCallback = Optional[Callable[[str], None]]


def calculate_crc16(data: bytes | bytearray) -> int:
    """CRC-16/XMODEM (poly 0x1021, init 0x0000) used by LEQI UART packets."""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def validate_serial_number(serial_number: str) -> str:
    """
    Validate scooter serial number.

    Must be exactly 19 ASCII characters.
    """
    if not isinstance(serial_number, str):
        raise ValueError("Serial number must be a string")
    if len(serial_number) != SERIAL_NUMBER_LENGTH:
        raise ValueError(
            f"Serial number must be exactly {SERIAL_NUMBER_LENGTH} characters "
            f"(got {len(serial_number)})"
        )
    try:
        serial_number.encode("ascii")
    except UnicodeEncodeError as e:
        raise ValueError(f"Serial number must contain only ASCII characters: {e}") from e
    return serial_number


def build_serial_packet(serial_number: str) -> bytes:
    """
    Build command 0x97 packet to set the scooter serial number.

    Packet: [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN...] [CRC_H] [CRC_L]
    """
    serial_number = validate_serial_number(serial_number)
    serial_bytes = serial_number.encode("ascii")
    sn_len = len(serial_bytes)

    packet = bytearray([
        0x5A,       # Header
        0x12,       # Immediate processing
        0x97,       # Set product serial
        sn_len + 1, # Length includes 0x30 field
        0x30,
    ])
    packet.extend(serial_bytes)

    crc = calculate_crc16(packet)
    packet.append((crc >> 8) & 0xFF)
    packet.append(crc & 0xFF)
    return bytes(packet)


def parse_response(data: bytes) -> Tuple[bool, Optional[str], str]:
    """
    Parse command 0x97 response.

    Expected: [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN...] [CRC_H] [CRC_L]

    Returns:
        (success, serial_number, message)
    """
    if len(data) < 8:
        return False, None, f"Response too short: {len(data)} bytes (expected at least 8)"

    if data[0] != 0x5A:
        return False, None, f"Invalid header: 0x{data[0]:02X} (expected 0x5A)"
    if data[1] != 0x12:
        return False, None, f"Invalid response command: 0x{data[1]:02X} (expected 0x12)"
    if data[2] != 0x97:
        return False, None, f"Invalid subcommand: 0x{data[2]:02X} (expected 0x97)"

    payload_len = data[3]
    if payload_len < 2:
        return False, None, f"Invalid length: {payload_len} (must be >= 2)"

    sn_len = payload_len - 1
    expected_len = 5 + sn_len + 2  # hdr/cmd/sub/len/0x30 + SN + CRC
    if len(data) < expected_len:
        return False, None, f"Response too short: {len(data)} bytes (expected {expected_len})"

    if data[4] != 0x30:
        return False, None, f"Invalid field marker: 0x{data[4]:02X} (expected 0x30)"

    try:
        serial_number = data[5:5 + sn_len].decode("ascii")
    except UnicodeDecodeError:
        return False, None, "Response contains non-ASCII serial number"

    crc_received = (data[5 + sn_len] << 8) | data[5 + sn_len + 1]
    crc_calculated = calculate_crc16(data[:5 + sn_len])
    if crc_received != crc_calculated:
        return (
            False,
            serial_number,
            f"CRC mismatch: got 0x{crc_received:04X}, expected 0x{crc_calculated:04X}",
        )

    return True, serial_number, "OK"


def list_serial_ports():
    """List available serial ports as (device, description) pairs."""
    ports = serial.tools.list_ports.comports()
    return [(p.device, p.description) for p in ports]


def _log(callback: LogCallback, message: str) -> None:
    if callback:
        callback(message)


def read_response(ser, timeout: float = 2.0, debug_callback: LogCallback = None) -> bytes:
    """Read one 0x97-style response packet from the serial port."""
    response = bytearray()
    start_time = time.time()

    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            byte = ser.read(1)
            if byte and byte[0] == 0x5A:
                response.append(byte[0])
                _log(debug_callback, "[RX] Found header byte 0x5A")
                break
        time.sleep(0.01)

    if not response:
        _log(debug_callback, "[RX] No response (timeout)")
        return bytes()

    # [cmd][subcmd][len][0x30]
    needed = 4
    while needed > 0 and time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(min(needed, ser.in_waiting))
            response.extend(chunk)
            needed -= len(chunk)
        time.sleep(0.01)

    if len(response) < 5:
        _log(debug_callback, "[RX] Incomplete response header")
        return bytes(response)

    sn_len = response[3] - 1
    total_len = 5 + sn_len + 2
    remaining = total_len - len(response)
    while remaining > 0 and time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(min(remaining, ser.in_waiting))
            response.extend(chunk)
            remaining -= len(chunk)
        time.sleep(0.01)

    _log(
        debug_callback,
        f"[RX] Response ({len(response)} bytes): {' '.join(f'{b:02X}' for b in response)}",
    )
    return bytes(response)


def send_serial_command(
    port: str,
    serial_number: str,
    baudrate: int = DEFAULT_BAUDRATE,
    timeout: float = 2.0,
    max_attempts: int = 10,
    debug_callback: LogCallback = None,
    simulation: bool = False,
) -> Tuple[bool, Optional[str], str]:
    """
    Send command 0x97 to set the scooter serial number.

    Returns:
        (success, response_serial, message)
    """
    try:
        packet = build_serial_packet(serial_number)
    except ValueError as e:
        return False, None, str(e)

    packet_hex = " ".join(f"{b:02X}" for b in packet)
    _log(debug_callback, f"[TX] Packet ({len(packet)} bytes): {packet_hex}")
    _log(debug_callback, f"     Serial: {serial_number}")
    _log(debug_callback, f"     CRC: 0x{packet[-2]:02X}{packet[-1]:02X}")

    if simulation:
        _log(debug_callback, f"[SIM] Port {port or '(none)'} @ {baudrate} baud")
        _log(debug_callback, f"[RX] Simulated ACK ({len(packet)} bytes): {packet_hex}")
        _log(debug_callback, f"[SIM] Scooter serial set to '{serial_number}'")
        return True, serial_number, "OK (simulated)"

    errors = []
    try:
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )
        try:
            _log(debug_callback, f"[INFO] Serial port opened: {port} @ {baudrate} baud")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(packet)
            _log(debug_callback, f"[INFO] Sent {len(packet)} bytes")

            for attempt in range(max_attempts):
                response = read_response(ser, timeout, debug_callback)
                if not response:
                    msg = f"Timeout waiting for response {attempt + 1}"
                    errors.append((False, None, msg))
                    _log(debug_callback, f"[ERROR] {msg}")
                    continue

                success, resp_serial, message = parse_response(response)
                if success and resp_serial == serial_number:
                    _log(debug_callback, f"[OK] Response {attempt + 1}: Serial number set successfully")
                    return True, resp_serial, "OK"

                errors.append((success, resp_serial, message))
                _log(debug_callback, f"[ERROR] Response {attempt + 1}: {message}")
        finally:
            ser.close()

        if errors:
            return errors[0]
        return False, None, "No valid response received"

    except serial.SerialException as e:
        return False, None, f"Serial error: {e}"
    except Exception as e:
        return False, None, f"Unexpected error: {e}"


def generate_serial_packet_hex(serial_number: str) -> Tuple[bool, Optional[str], str]:
    """Generate hex packet string without sending."""
    try:
        packet = build_serial_packet(serial_number)
        return True, " ".join(f"{b:02X}" for b in packet), "OK"
    except ValueError as e:
        return False, None, str(e)
