#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher - Firmware Type Detector
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

import struct
from typing import Tuple

from bwflasher.base_flasher import FirmwareType


def detect_firmware_type(firmware_data: bytes) -> FirmwareType:
    """
    Detect firmware type from binary data.

    This function analyzes the firmware header to determine if it's:
    - Brightway firmware (has DEPRD5C signature and 637C pattern)
    - Leqi firmware (encrypted with XOR 0xAA, has 'aa a2' patterns)
    - Unknown format

    Args:
        firmware_data: Binary firmware data

    Returns:
        FirmwareType enum value
    """
    if len(firmware_data) < 0x1000:
        return FirmwareType.UNKNOWN

    # Check for Brightway firmware signature "DEPRD5C" at offset 0x800
    if len(firmware_data) > 0x808:
        signature_region = firmware_data[0x800:0x808]
        if signature_region == b'DEPRD5C\x00':
            return FirmwareType.BRIGHTWAY

    # Alternative Brightway check: look for 637C pattern (used for signing)
    # This pattern should exist exactly once in Brightway firmware
    try:
        from bwflasher.utils import find_pattern_offsets
        offsets = find_pattern_offsets("637C", firmware_data)
        if len(offsets) == 1 and offsets[0] > 0x1000:
            return FirmwareType.BRIGHTWAY
    except:
        pass

    # Check for Leqi firmware (encrypted with 0xAA)
    # Look for the characteristic "aa a2" pattern (0xAA XORed address in little-endian)
    # and high concentration of 0xAA bytes
    aa_a2_pattern = b'\xaa\xa2'
    aa_a2_count = firmware_data[0x80:0x400].count(aa_a2_pattern)
    aa_count = firmware_data[0x80:0x400].count(0xAA)

    # Leqi encrypted firmware has many "aa a2" patterns (encrypted pointers)
    # and overall high 0xAA byte concentration
    if aa_a2_count > 10 and aa_count > 50:
        return FirmwareType.LEQI

    return FirmwareType.UNKNOWN


def detect_firmware_file(firmware_file: str) -> FirmwareType:
    """
    Detect firmware type from file path.

    Args:
        firmware_file: Path to firmware file

    Returns:
        FirmwareType enum value
    """
    try:
        with open(firmware_file, 'rb') as f:
            firmware_data = f.read()  # Read entire file for detection
        return detect_firmware_type(firmware_data)
    except Exception:
        return FirmwareType.UNKNOWN


def get_firmware_info(firmware_data: bytes) -> Tuple[FirmwareType, dict]:
    """
    Get detailed firmware information.

    Args:
        firmware_data: Binary firmware data

    Returns:
        Tuple of (FirmwareType, info_dict)
        info_dict contains type-specific information
    """
    fw_type = detect_firmware_type(firmware_data)
    info = {
        'type': fw_type,
        'size': len(firmware_data),
    }

    if fw_type == FirmwareType.BRIGHTWAY:
        # Extract Brightway firmware info
        if len(firmware_data) > 0x808:
            signature = firmware_data[0x800:0x807].decode('ascii', errors='ignore')
            info['signature'] = signature

        try:
            from bwflasher.utils import find_pattern_offsets
            offsets = find_pattern_offsets("637C", firmware_data)
            if offsets:
                info['signing_pattern_offset'] = f"0x{offsets[0]:X}"
        except:
            pass

        info['protocol'] = "DFU (Device Firmware Update)"

    elif fw_type == FirmwareType.LEQI:
        # Extract Leqi firmware info
        aa_a2_count = firmware_data[0x80:0x400].count(b'\xaa\xa2')
        aa_count = firmware_data[0x80:0x400].count(0xAA)
        info['encryption'] = "XOR 0xAA"
        info['aa_a2_pattern_count'] = aa_a2_count
        info['aa_byte_count'] = aa_count
        info['protocol'] = "Binary packets (5A 12 header)"

    return fw_type, info


def create_flasher_for_firmware(firmware_file: str, **kwargs):
    """
    Factory function to create the appropriate flasher for a firmware file.

    Args:
        firmware_file: Path to firmware file
        **kwargs: Additional arguments to pass to flasher constructor

    Returns:
        Instance of BrightwayFlasher or LeqiFlasher

    Raises:
        ValueError: If firmware type cannot be determined
    """
    from bwflasher.brightway_flasher import BrightwayFlasher
    from bwflasher.leqi_flasher import LeqiFlasher

    fw_type = detect_firmware_file(firmware_file)

    if fw_type == FirmwareType.BRIGHTWAY:
        return BrightwayFlasher(**kwargs)
    elif fw_type == FirmwareType.LEQI:
        return LeqiFlasher(**kwargs)
    else:
        raise ValueError(f"Unknown firmware type for file: {firmware_file}")
