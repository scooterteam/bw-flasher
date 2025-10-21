#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher - Leqi Firmware Flasher
# Copyright (C) 2024-2025 ScooterTeam
#
# This work is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-nc-sa/4.0/
# or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

import serial
import struct
import time
from serial.serialutil import SerialException

from bwflasher.base_flasher import BaseFlasher, FlasherException, FirmwareType


class LeqiFlasher(BaseFlasher):
    """Flasher for Leqi scooter firmware (encrypted with XOR 0xAA)"""

    # Constants from reverse engineering
    ENCRYPTION_KEY = 0xAA
    CRC16_POLY = 0x1021  # CRC-16/XMODEM polynomial (for packet validation)
    CRC16_POLY_FIRMWARE = 0x8005  # CRC-16 polynomial for firmware validation (with bit reversal)
    CHUNK_SIZE = 128
    PACKET_HEADER = b'\x5A\x12'

    def __init__(
        self,
        tty_port: str = "/dev/ttyUSB0",
        simulation: bool = False,
        debug: bool = False,
        status_callback=None,
        progress_callback=None,
        log_callback=None
    ):
        super().__init__(tty_port, simulation, debug, status_callback, progress_callback, log_callback)
        self.serial_conn = None
        self.encrypted_fw = None
        self.fw_size = 0
        self.session_start_time = None

    def load_file(self, firmware_file: str):
        """Load and validate Leqi firmware file"""
        self.debug_log(f"Loading Leqi firmware file: {firmware_file}")

        with open(firmware_file, 'rb') as f:
            self.fw = f.read()

        # Check if it's encrypted firmware (should have 0xAA patterns)
        if self.detect_firmware_type(self.fw) != FirmwareType.LEQI:
            raise FlasherException("This doesn't appear to be a Leqi firmware file")

        self.encrypted_fw = self.fw
        self.fw_size = self.calculate_firmware_size(self.encrypted_fw)

        self.log(f"Loaded Leqi firmware: {len(self.fw)} bytes")
        self.log(f"Firmware size (AA padding end): 0x{self.fw_size:X} ({self.fw_size} bytes)")

    def run(self):
        """Execute the Leqi firmware flashing process"""
        if not self.encrypted_fw:
            raise FlasherException("No firmware loaded. Call load_file() first.")

        if self.simulation:
            self.log("Simulation mode - running simulated Leqi firmware flash")
            self._run_simulation()
            return

        try:
            # Open serial port
            self.serial_conn = serial.Serial(
                port=self.tty_port,
                baudrate=19200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=2.0
            )

            self.log(f"Serial port opened: {self.tty_port} @ 19200 baud")
            self.session_start_time = time.time()

            # Flush buffers
            self.serial_conn.reset_input_buffer()
            self.serial_conn.reset_output_buffer()

            # Step 1: Send firmware update start command
            self.emit_status("Sending firmware update start command...")
            self._send_start_command()

            # Step 2: Send firmware data in chunks
            self.emit_status("Sending firmware data...")
            self._send_firmware_data()

            # Step 3: Send firmware update end command
            self.emit_status("Finalizing firmware update...")
            self._send_end_command()

            self.serial_conn.close()
            self.log("✓ SUCCESS: Leqi firmware update completed")
            self.emit_progress(100)

        except SerialException as e:
            raise FlasherException(f"Serial port error: {e}")
        except Exception as e:
            raise FlasherException(f"Unexpected error: {e}")

    def _run_simulation(self):
        """Run simulated Leqi firmware flash with TX/RX logging"""
        import time

        # Simulate start command
        self.emit_status("SIMULATION: Sending firmware update start command...")
        start_packet = bytearray([0x5A, 0x12, 0x03, 0x06])
        start_packet.append(0x31)
        start_packet.append(0x00)
        start_packet.extend(struct.pack('<H', self.fw_size))
        start_packet.extend([0x00, 0x00])
        crc = self.crc16_standard(start_packet)
        start_packet.extend(struct.pack('>H', crc))

        tx_hex = ' '.join(f'{b:02X}' for b in start_packet)
        self.debug_log(f"TX: {tx_hex}")
        time.sleep(0.044)  # 44ms delay

        # Simulate start response
        start_response = bytes([0x5A, 0x21, 0x03, 0x01, 0x01, 0x68, 0x26])
        rx_hex = ' '.join(f'{b:02X}' for b in start_response)
        self.debug_log(f"RX: {rx_hex}")
        self.emit_progress(5)

        # Simulate firmware data chunks
        self.emit_status("SIMULATION: Sending firmware data...")
        total_chunks = (self.fw_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

        for chunk_num in range(1, total_chunks + 1):
            offset = (chunk_num - 1) * self.CHUNK_SIZE
            chunk_end = min(offset + self.CHUNK_SIZE, self.fw_size)
            chunk_data = self.encrypted_fw[offset:chunk_end]

            # Pad last chunk to 128 bytes
            if len(chunk_data) < self.CHUNK_SIZE:
                chunk_data = chunk_data + b'\xFF' * (self.CHUNK_SIZE - len(chunk_data))

            # Build full packet with data and CRC
            packet = bytearray([0x5A, 0x12, 0x04, 0x84])
            packet.extend(struct.pack('<I', offset))
            packet.extend(chunk_data)
            crc = self.crc16_standard(packet)
            packet.extend(struct.pack('>H', crc))

            # Only log every 10th chunk to avoid spam
            if chunk_num % 10 == 0 or chunk_num == 1:
                tx_hex = ' '.join(f'{b:02X}' for b in packet)
                self.debug_log(f"TX: {tx_hex}")

                # Simulate response
                data_response = bytes([0x5A, 0x21, 0x04, 0x01, 0x01, 0xED, 0xB6])
                rx_hex = ' '.join(f'{b:02X}' for b in data_response)
                self.debug_log(f"RX: {rx_hex}")

                progress = 5 + int((chunk_num / total_chunks) * 85)
                self.emit_progress(progress)

                progress_msg = f"Progress: {chunk_num}/{total_chunks} chunks ({progress}%)"
                if self.debug:
                    self.emit_status(progress_msg)
                else:
                    self.log(progress_msg)

            time.sleep(0.044)  # 44ms delay between chunks

        self.emit_status("SIMULATION: Finalizing firmware update...")
        self.emit_progress(95)

        # Simulate end command
        end_packet = bytearray([0x5A, 0x12, 0x05, 0x00])
        crc = self.crc16_standard(end_packet)
        end_packet.extend(struct.pack('>H', crc))
        tx_hex = ' '.join(f'{b:02X}' for b in end_packet)
        self.debug_log(f"TX: {tx_hex}")
        time.sleep(0.044)  # 44ms delay

        # Simulate end response
        end_response = bytes([0x5A, 0x21, 0x05, 0x01, 0x01, 0x55, 0xA7])
        rx_hex = ' '.join(f'{b:02X}' for b in end_response)
        self.debug_log(f"RX: {rx_hex}")

        self.log("✓ SIMULATION: Leqi firmware update completed successfully")
        self.emit_progress(100)

    def test_connection(self):
        """Test connection to Leqi controller"""
        if self.simulation:
            self.log("Simulation mode - testing Leqi protocol")
            self.emit_status("Simulating connection test...")

            # Simulate sending a test packet
            test_packet = bytearray([0x5A, 0x12, 0x03, 0x06, 0x31, 0x00, 0x00, 0x10, 0x00, 0x00])
            crc = self.crc16_standard(test_packet)
            test_packet.extend(struct.pack('>H', crc))

            tx_hex = ' '.join(f'{b:02X}' for b in test_packet)
            self.debug_log(f"TX (simulated): {tx_hex}")

            # Simulate response
            response = bytes([0x5A, 0x21, 0x03, 0x01, 0x01, 0x68, 0x26])
            rx_hex = ' '.join(f'{b:02X}' for b in response)
            self.debug_log(f"RX (simulated): {rx_hex}")

            self.log("✓ Simulation successful")
            self.emit_progress(100)
            return

        try:
            self.serial_conn = serial.Serial(
                port=self.tty_port,
                baudrate=19200,
                timeout=1.0
            )
            self.log(f"✓ Successfully opened port: {self.tty_port}")
            self.serial_conn.close()
            self.emit_progress(100)
        except SerialException as e:
            raise FlasherException(f"Connection test failed: {e}")

    @staticmethod
    def detect_firmware_type(firmware_data: bytes) -> FirmwareType:
        """Detect if firmware is Leqi type (encrypted with 0xAA)"""
        if len(firmware_data) < 0x400:
            return FirmwareType.UNKNOWN

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

    def bit_reverse_8(self, value):
        """Reverse bits in an 8-bit value"""
        result = 0
        for i in range(8):
            if value & (1 << i):
                result |= 1 << (7 - i)
        return result & 0xFF

    def bit_reverse_16(self, value):
        """Reverse bits in a 16-bit value"""
        result = 0
        for i in range(16):
            if value & (1 << i):
                result |= 1 << (15 - i)
        return result & 0xFFFF

    def crc16_standard(self, data):
        """CRC-16/XMODEM for packet verification"""
        crc = 0x0000
        for byte in data:
            crc ^= byte << 8
            for _ in range(8):
                if crc & 0x8000:
                    crc = ((crc << 1) ^ self.CRC16_POLY) & 0xFFFF
                else:
                    crc = (crc << 1) & 0xFFFF
        return crc & 0xFFFF

    def calculate_firmware_size(self, firmware_data):
        """Calculate firmware size by finding end of AA padding"""
        data = bytes(firmware_data)
        max_aa_length = 0
        max_aa_end = 0

        i = 0
        while i < len(data):
            if data[i] == 0xAA:
                start = i
                while i < len(data) and data[i] == 0xAA:
                    i += 1
                length = i - start

                if length > max_aa_length and length > 500:
                    max_aa_length = length
                    max_aa_end = i
            else:
                i += 1

        if max_aa_end > 0:
            fw_size = ((max_aa_end + 127) // 128) * 128
            self.debug_log(f"Found {max_aa_length} consecutive AA bytes ending at 0x{max_aa_end:X}")
            self.debug_log(f"Rounded up to: 0x{fw_size:X}")
            return fw_size
        else:
            return len(data)

    def _send_start_command(self):
        """Send firmware update start command (0x03)"""
        start_packet = bytearray([0x5A, 0x12, 0x03, 0x06])
        start_packet.append(0x31)  # Version/flag byte
        start_packet.append(0x00)  # Padding
        start_packet.extend(struct.pack('<H', self.fw_size))  # Firmware size (16-bit LE)
        start_packet.extend([0x00, 0x00])  # Padding

        crc = self.crc16_standard(start_packet)
        start_packet.extend(struct.pack('>H', crc))

        response = self._send_and_receive(start_packet, "Start", expected_len=7)

        if not response or len(response) < 5 or response[1] != 0x21 or response[2] != 0x03:
            raise FlasherException("Invalid start response from controller")

        self.log("✓ Start command acknowledged")

    def _send_firmware_data(self):
        """Send firmware data in 128-byte chunks"""
        offset = 0
        chunk_num = 0
        failed_chunks = 0
        total_chunks = (self.fw_size + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE

        while offset < self.fw_size:
            chunk_end = min(offset + self.CHUNK_SIZE, self.fw_size)
            chunk_data = self.encrypted_fw[offset:chunk_end]

            # Pad last chunk to 128 bytes
            if len(chunk_data) < self.CHUNK_SIZE:
                chunk_data = chunk_data + b'\xFF' * (self.CHUNK_SIZE - len(chunk_data))

            # Build packet: [5A] [12] [04] [LEN=0x84] [OFFSET32_LE] [DATA×128] [CRC_H] [CRC_L]
            packet = bytearray([0x5A, 0x12, 0x04, 0x84])
            packet.extend(struct.pack('<I', offset))
            packet.extend(chunk_data)

            crc = self.crc16_standard(packet)
            packet.extend(struct.pack('>H', crc))

            chunk_num += 1
            response = self._send_and_receive(packet, f"Chunk {chunk_num} @ 0x{offset:04X}", expected_len=7)

            if not response:
                self.log(f"WARNING: No response for chunk {chunk_num}")
                failed_chunks += 1
            elif len(response) < 5 or response[1] != 0x21 or response[2] != 0x04:
                self.log(f"WARNING: Invalid response format for chunk {chunk_num}")
                failed_chunks += 1
            elif len(response) >= 5 and response[4] != 0x01:
                self.log(f"ERROR: Chunk {chunk_num} REJECTED (status=0x{response[4]:02X})")
                failed_chunks += 1

            offset = chunk_end

            # Update progress
            progress = int((chunk_num / total_chunks) * 90)  # 0-90% for data transfer
            self.emit_progress(progress)

            if chunk_num % 10 == 0:
                progress_msg = f"Progress: {chunk_num}/{total_chunks} chunks ({progress}%)"
                if self.debug:
                    self.emit_status(progress_msg)
                else:
                    self.log(progress_msg)

            # Delay between chunks
            time.sleep(0.044)

        if failed_chunks > 0:
            raise FlasherException(f"{failed_chunks} chunks had invalid/missing responses")

        self.log(f"✓ Sent {chunk_num} chunks successfully")

        # Wait for controller to process
        time.sleep(0.69)

    def _send_end_command(self):
        """Send firmware update end command (0x05)"""
        end_packet = bytearray([0x5A, 0x12, 0x05, 0x00])
        crc = self.crc16_standard(end_packet)
        end_packet.extend(struct.pack('>H', crc))

        # Retry end command up to 10 times
        response = None
        max_retries = 10
        end_timeout = 0.4

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                self.log(f"Retry {attempt}/{max_retries}...")
                time.sleep(0.06)

            response = self._send_and_receive(
                end_packet,
                f"End (attempt {attempt})",
                expected_len=7,
                timeout=end_timeout
            )

            if response and len(response) >= 5 and response[1] == 0x21 and response[2] == 0x05:
                break

            response = None

        if not response:
            raise FlasherException(f"No valid response to end command after {max_retries} attempts")

        self.log("✓ End command acknowledged")

    def _send_and_receive(self, packet, description, expected_len=7, timeout=None):
        """Send packet and read response"""
        if timeout is None:
            timeout = 2.0

        # Flush input buffer
        self.serial_conn.reset_input_buffer()

        # Send packet
        tx_time = time.time()
        self.serial_conn.write(packet)
        self.serial_conn.flush()

        tx_hex = ' '.join(f'{b:02X}' for b in packet)
        self.debug_log(f"TX [{description}]: {tx_hex}")

        # Small delay for controller to respond
        time.sleep(0.05)

        # Read response
        response = bytearray()
        start_time = time.time()

        # Look for header byte (0x5A)
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                byte = self.serial_conn.read(1)
                if byte[0] == 0x5A:
                    response.append(byte[0])
                    break
            time.sleep(0.01)

        if len(response) == 0:
            self.debug_log(f"RX: <timeout after {timeout}s>")
            return None

        # Read rest of response
        while time.time() - start_time < timeout:
            if self.serial_conn.in_waiting > 0:
                byte = self.serial_conn.read(1)
                response.append(byte[0])
                if len(response) >= expected_len:
                    break
            elif len(response) >= 5:
                time.sleep(0.02)
                if self.serial_conn.in_waiting == 0:
                    break
            time.sleep(0.01)

        rx_hex = ' '.join(f'{b:02X}' for b in response)
        self.debug_log(f"RX: {rx_hex} ({len(response)} bytes)")

        return bytes(response)
