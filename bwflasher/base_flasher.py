#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.
#
# You are free to:
# - Share — copy and redistribute the material in any medium or format
# - Adapt — remix, transform, and build upon the material
#
# Under the following terms:
# - Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made.
# - NonCommercial — You may not use the material for commercial purposes.
# - ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original.
#

from abc import ABC, abstractmethod
from enum import Enum
from typing import Tuple

from bwflasher.utils import load_and_process_firmware, process_firmware


class FirmwareType(Enum):
    """Enum to identify firmware types"""
    BRIGHTWAY = "Brightway"
    LEQI = "LEQI"
    NINEBOT = "Ninebot"
    UNKNOWN = "Unknown"


class FlasherException(Exception):
    """Base exception for flasher operations"""
    pass


class BaseFlasher(ABC):
    """Abstract base class for firmware flashers"""

    def __init__(
        self,
        tty_port: str = "/dev/ttyUSB0",
        simulation: bool = False,
        debug: bool = False,
        status_callback=None,
        progress_callback=None,
        log_callback=None
    ):
        self.tty_port = tty_port
        self.simulation = simulation
        self.debug = debug
        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.fw = None

    @abstractmethod
    def load_file(self, firmware_file: str):
        """Load firmware file"""
        pass

    @abstractmethod
    def run(self):
        """Execute the flashing process"""
        pass

    @abstractmethod
    def test_connection(self):
        """Test connection to device"""
        pass

    @staticmethod
    @abstractmethod
    def detect_firmware_type(firmware_data: bytes) -> FirmwareType:
        """Detect the firmware type from binary data"""
        pass

    def log(self, *message):
        """Log a message via callback"""
        if self.log_callback:
            self.log_callback(' '.join(str(m) for m in message))

    def debug_log(self, *message):
        """Log a debug message"""
        if not self.debug:
            return
        self.log("(DEBUG)", ' '.join(str(m) for m in message))

    def emit_progress(self, percentage: int):
        """Emit progress update"""
        if self.progress_callback:
            self.progress_callback(percentage)

    def emit_status(self, status_text: str):
        """Emit status update"""
        if self.status_callback:
            self.status_callback(status_text)

def _get_flasher_classes():
    from bwflasher.brightway_flasher import BrightwayFlasher
    from bwflasher.leqi_flasher import LeqiFlasher
    #from bwflasher.ninebot_flasher import NinebotFlasher
    return [BrightwayFlasher, LeqiFlasher]

def detect_firmware_type(firmware_data: bytes) -> FirmwareType:
    for flasher_class in _get_flasher_classes():
        fw_type = flasher_class.detect_firmware_type(firmware_data)
        if fw_type != FirmwareType.UNKNOWN:
            return fw_type
    return FirmwareType.UNKNOWN

def detect_firmware_file(firmware_file: str) -> FirmwareType:
    try:
        firmware_data = load_and_process_firmware(firmware_file)
        return detect_firmware_type(firmware_data)
    except Exception:
        return FirmwareType.UNKNOWN

def create_flasher_for_firmware(firmware_file: str, **kwargs):
    fw_type = detect_firmware_file(firmware_file)
    for flasher_class in _get_flasher_classes():
        if flasher_class.detect_firmware_type(load_and_process_firmware(firmware_file)) == fw_type:
            return flasher_class(**kwargs)
    raise ValueError(f"Unknown firmware type for file: {firmware_file}")

def get_firmware_info(firmware_data: bytes) -> Tuple[FirmwareType, dict]:
    data = process_firmware(firmware_data)
    fw_type = detect_firmware_type(data)
    info = {
        'type': fw_type,
        'size': len(data),
    }

    if fw_type == FirmwareType.BRIGHTWAY:
        if len(data) > 0x808:
            signature = data[0x800:0x807].decode('ascii', errors='ignore')
            info['signature'] = signature
        try:
            from bwflasher.utils import find_pattern_offsets
            offsets = find_pattern_offsets("637C", data)
            if offsets:
                info['signing_pattern_offset'] = f"0x{offsets[0]:X}"
        except:
            pass
        info['protocol'] = "DFU (Device Firmware Update)"

    elif fw_type == FirmwareType.LEQI:
        aa_a2_count = data[0x80:0x400].count(b'\xaa\xa2')
        aa_count = data[0x80:0x400].count(0xAA)
        info['encryption'] = "XOR 0xAA"
        info['aa_a2_pattern_count'] = aa_a2_count
        info['aa_byte_count'] = aa_count
        info['protocol'] = "Binary packets (5A 12 header)"
    elif fw_type == FirmwareType.NINEBOT:
        try:
            version_offset = data.find(b'\x00', 0x107) + 1
            version_end = data.find(b'\x00', version_offset)
            info['version'] = data[version_offset:version_end].decode('ascii')
        except:
            info['version'] = 'Unknown'
        info['protocol'] = "Ninebot (55 AA header)"

    return fw_type, info

