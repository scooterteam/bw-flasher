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

import serial
import binascii
import math
import time
import os

from enum import Enum

from bwflasher.utils import find_pattern_offsets
from bwflasher.keygen import sign_rand


class FlasherException(Exception):
    pass


class DFUState(Enum):
    UID = "UID"
    VER_INIT = "VER_INIT"
    INIT = "INIT"
    BLE_RAND = "BLE_RAND"
    MCU_RAND = "MCU_RAND"
    MCU_KEY = "MCU_KEY"
    NVM_WRITE = "NVM_WRITE"
    SEND_FW = "SEND_FW"
    WR_INFO = "WR_INFO"
    DFU_VERIFY = "DFU_VERIFY"
    DFU_ACTIVE = "DFU_ACTIVE"
    VER_DONE = "VER_DONE"
    DONE = "DONE"


def calculate_crc16(data: bytearray) -> int:
    """Calculate CRC16 for the given data."""
    return binascii.crc_hqx(data, 0x0)


def calculate_crc32(data: bytearray) -> int:
    """Calculate CRC32 for the given data."""
    return binascii.crc32(data)


class DFU:
    PACKET_SIZE = 0x800
    CHUNK_SIZE = 0x80
    CHUNKS_PER_PACKET = PACKET_SIZE // CHUNK_SIZE
    MAX_REPEATS = 20

    def __init__(
        self,
        tty_port: str = "/dev/ttyUSB0",
        simulation: bool = False,
        debug: bool = False,
        status_callback=None,
        progress_callback=None,
        log_callback=None
    ):
        self.simulation = simulation
        self.debug = debug
        self.simulation_tx_buf = None
        self.ble_rand = bytearray(range(1, 17))  # BLE_RAND from 01 to 10
        self.mcu_rand = None
        self.retries = 0
        self.prev_state = DFUState.UID
        self.state = DFUState.UID
        self.fw = None
        self.packet = None
        self.data_sent = bytes()
        self.total_packets = 0
        self.total_chunks = 0
        self.n_packets_sent = 0
        self.fw_offsets = []

        self.status_callback = status_callback
        self.progress_callback = progress_callback
        self.log_callback = log_callback

        if not simulation:
            self.serial_conn = serial.Serial(tty_port, baudrate=19200, timeout=0.1)
        else:
            self.serial_conn = None  # No serial connection in simulation mode

    def __find_fw_offsets(self):
        offsets = find_pattern_offsets("637C", self.fw)
        if len(offsets) != 1:
            raise FlasherException("Invalid / unsupported firmware file")
        offset_0 = offsets[0]

        offsets = find_pattern_offsets("0102", self.fw, start_offset=offset_0)
        if len(offsets) != 1:
            raise FlasherException("Invalid / unsupported firmware file")
        offset_1 = offsets[0] - 1
        self.fw_offsets = [offset_0, offset_1]

    def load_file(self, firmware_file):
        self.debug_log("Loading firmware file")
        with open(firmware_file, 'rb') as fw:
            self.fw = fw.read()

        self.__find_fw_offsets()

        self.total_packets = math.ceil(len(self.fw) / self.PACKET_SIZE)
        self.total_chunks = self.total_packets * self.CHUNKS_PER_PACKET

    def log(self, *message):
        if self.log_callback:
            self.log_callback(' '.join(message))

    def debug_log(self, *message):
        if not self.debug:
            return
        self.log("(DEBUG)", ' '.join(message))

    def emit_state(self, state_text):
        if self.prev_state != self.state:
            if self.status_callback:
                self.status_callback(state_text)

        self.prev_state = self.state

    def emit_progress(self):
        if self.progress_callback:
            perc = int(self.n_packets_sent / self.total_packets * 100)
            self.progress_callback(perc)

    def run(self):
        while self.state != DFUState.DONE:
            if self.state == DFUState.UID:
                self.emit_state(f"{self.state} -> Fetching UID")
                self.get_uid()
            elif self.state == DFUState.VER_INIT:
                self.emit_state(f"{self.state} -> Sending 'get_ver'")
                self.get_ver()
            elif self.state == DFUState.INIT:
                self.emit_state(f"{self.state} -> Sending 'rd_info'")
                self.send_rd_info()
            elif self.state == DFUState.BLE_RAND:
                self.emit_state(f"{self.state} -> Sending BLE_RAND")
                self.send_ble_rand()
            elif self.state == DFUState.MCU_RAND:
                self.emit_state(f"{self.state} -> Requesting MCU_RAND")
                self.request_mcu_rand()
            elif self.state == DFUState.MCU_KEY:
                self.emit_state(f"{self.state} -> Sending MCU_KEY")
                self.send_mcu_key()
            elif self.state == DFUState.NVM_WRITE:
                self.emit_state(f"{self.state} -> Sending NVM Write")
                self.send_nvm_write()
            elif self.state == DFUState.SEND_FW:
                self.emit_state(f"{self.state} -> Sending Firmware Packet")
                self.send_fw_packet()
            elif self.state == DFUState.WR_INFO:
                self.emit_state(f"{self.state} -> Sending WR_INFO")
                self.send_wr_info()
            elif self.state == DFUState.DFU_VERIFY:
                self.emit_state(f"{self.state} -> Verifying DFU")
                self.verify_dfu()
            elif self.state == DFUState.DFU_ACTIVE:
                self.emit_state(f"{self.state} -> Activating DFU")
                self.activate_dfu()
            elif self.state == DFUState.VER_DONE:
                self.emit_state(f"{self.state} -> Sending 'get_ver'")
                self.get_ver()
            else:
                raise FlasherException(f"Unknown state: {self.state}")

            self.emit_progress()
        self.emit_state(f"{self.state} -> Enjoy!")

    def test_connection(self):
        retries = 0
        while self.state != DFUState.INIT:
            if self.state != self.prev_state:
                retries = 0

            if retries == self.MAX_REPEATS:
                raise FlasherException("Max retries reached. Check your connection.")

            if self.state == DFUState.UID:
                self.emit_state(f"{self.state} -> Fetching UID")
                self.get_uid()
            elif self.state == DFUState.VER_INIT:
                self.emit_state(f"{self.state} -> Sending 'get_ver'")
                self.get_ver()

            retries += 1

        self.log(f"{self.state} -> Successfully established connection!")
        self.progress_callback(100)

    def get_uid(self):
        byte_start = b'\x64'
        byte_end = b'\x9B'

        cmd_get_uid = bytes.fromhex("53 2A 7D AC")
        self.send(cmd_get_uid)
        response = self.receive_response(21, expected_byte=byte_end)

        if byte_start in response and byte_end in response:
            response = response[
                response.index(byte_start):response.index(byte_end)
            ]
            if response[1] == cmd_get_uid[1] and response[2] == 0x10:
                self.uid = response[3:3+0x10]
                self.log("> Got UID: " + self.uid.decode())
                self.state = DFUState.VER_INIT

    def get_ver(self):
        self.send(b'down get_ver\r')
        response = self.receive_response(5)
        if b'\r' in response[-2:]:
            ver = response.split(b'\r')[0].decode()
            if self.state == DFUState.VER_INIT:
                self.log("> MCU Version (before): " + ver)
                self.state = DFUState.INIT
            elif self.state == DFUState.VER_DONE:
                self.log("> MCU Version (after): " + ver)
                self.state = DFUState.DONE

    def send_rd_info(self):
        self.send(b'down rd_info\r\x00\x00\x00')
        response = self.receive_response(26)
        if response.startswith(b'ok'):
            self.state = DFUState.BLE_RAND

    def send_ble_rand(self):
        ble_key_expected = sign_rand(self.uid, self.ble_rand, self.fw, self.fw_offsets[0], self.fw_offsets[1])

        self.send(b'down ble_rand ' + self.ble_rand + b'\r')
        response = self.receive_response(20)
        if response.startswith(b'ok'):
            self.state = DFUState.MCU_RAND
            ble_key = response[3:19]  # Simulating extraction of BLE_KEY
            self.debug_log("BLE_KEY:", ble_key.hex(' '))
            if ble_key != ble_key_expected:
                raise FlasherException("BLE_KEY does not match! Correct UID?")

    def request_mcu_rand(self):
        self.send(b'down mcu_rand\r')
        response = self.receive_response(20)
        if response.startswith(b'ok'):
            self.mcu_rand = response[3:19]  # Simulating extraction of MCU_RAND
            self.debug_log("MCU_RAND:", self.mcu_rand.hex(' '))
            self.state = DFUState.MCU_KEY

    def send_mcu_key(self):
        mcu_key = sign_rand(self.uid, self.mcu_rand, self.fw, self.fw_offsets[0], self.fw_offsets[1])
        self.send(b'down mcu_key ' + mcu_key + b'\r')
        response = self.receive_response(3)
        if response == b'ok\r':
            self.state = DFUState.NVM_WRITE

    def send_nvm_write(self):
        packet_start = self.n_packets_sent * self.PACKET_SIZE
        packet_end = (self.n_packets_sent + 1) * self.PACKET_SIZE
        self.packet = self.fw[packet_start:packet_end]

        loc = self.n_packets_sent * self.PACKET_SIZE
        send_str = f"down nvm_write {loc:08X}"
        self.debug_log(send_str)
        self.send(send_str.encode() + b'\r')
        response = self.receive_response(3)
        if b'k\r' in response:
            self.state = DFUState.SEND_FW

    def send_fw_packet(self):
        if self.packet:
            if len(self.packet) < self.PACKET_SIZE:
                self.packet += b'\xFF' * (self.PACKET_SIZE - len(self.packet))
            assert len(self.packet) == self.PACKET_SIZE
            for n in range(self.CHUNKS_PER_PACKET):
                chunk_start = n * self.CHUNK_SIZE
                chunk_end = chunk_start + self.CHUNK_SIZE
                data_chunk = self.packet[chunk_start:chunk_end]

                N = (n + 1).to_bytes(1, 'big')
                N_ = (0xFF - (n + 1)).to_bytes(1, 'big')
                crc16 = calculate_crc16(data_chunk).to_bytes(2, 'big')
                packet = b'\x01' + N + N_ + data_chunk + crc16

                for repeat in range(self.MAX_REPEATS):
                    self.send(packet)
                    response = self.receive_response(1, expected_byte=b'\x06')
                    if response == b'\x06':
                        break
                    elif response == b'\x15':
                        raise FlasherException("CRC fail")
                    elif not response:
                        continue
                if repeat + 1 == self.MAX_REPEATS:
                    raise FlasherException(f"No valid ACK after {self.MAX_REPEATS} retries. Check serial adapter (driver / settings) and make sure the firmware file is valid for this device.")

        # this part is actually only needed somewhere after 70%...
        self.send(b'\x04\x04\x04')
        response = self.receive_response(3, expected_byte=b'\x06')
        if b'\x06' not in response:
            pass
            #print("Warn: missing confirmation")
        #    raise FlasherException("Unexpected response")

        # count up for the last message, even if no packet sent
        self.n_packets_sent += 1
        self.data_sent += self.packet

        self.state = DFUState.WR_INFO

    def send_wr_info(self):

        packet_crc32 = calculate_crc32(self.data_sent).to_bytes(4, 'big')
        cmd = (
            'down wr_info '
            + str(self.n_packets_sent) + ' '
            + str(packet_crc32.hex()) + ' '
            + str(self.n_packets_sent * self.PACKET_SIZE) + '\r'
        )
        self.debug_log(cmd)
        self.send(cmd.encode())
        response = self.receive_response(3)
        if b'k\r' in response:
            if self.packet:
                self.state = DFUState.NVM_WRITE
            else:
                self.state = DFUState.DFU_VERIFY

    def verify_dfu(self):
        self.send(b'down dfu_verify\r')
        response = self.receive_response(3)
        if b'k\r' in response:
            self.debug_log("Firmware update verified successfully!")
            self.state = DFUState.DFU_ACTIVE
        elif b'r\r' in response:
            raise FlasherException("Verify failed")

    def activate_dfu(self):
        self.send(b'down dfu_active\r')
        response = self.receive_response(3)
        if b'k\r' in response:
            self.log("> Firmware update completed successfully!")
            self.state = DFUState.VER_DONE
        elif b'r\r' in response:  # 'error\r'
            raise FlasherException("Activate failed")

    def send(self, data: bytearray):
        self.debug_log("Sending:", data.hex(' ').upper())
        if self.simulation:
            self.simulation_tx_buf = data
        else:
            self.serial_conn.write(data)
            self.serial_conn.flush()

    def receive_response(self, expected_n_bytes, expected_byte='\r') -> bytes:
        if self.simulation:
            time.sleep(0.01)
            # Simulate different responses based on state
            if self.state == DFUState.UID:
                uid = "foobarfoobar1337".encode().hex()
                return bytes.fromhex(f"64 2A 10 {uid} 10 9B")
            elif self.state in [DFUState.VER_INIT, DFUState.VER_DONE]:
                return b'0010\r'
            elif self.state == DFUState.BLE_RAND:
                ble_key = bytes.fromhex("c9539e4579936b213d6740ee1857d8b2")
                return b'ok ' + ble_key + b'\r'
            elif self.state == DFUState.MCU_RAND:
                mcu_rand = os.urandom(16)
                return b'ok ' + mcu_rand + b'\r'
            elif self.state == DFUState.SEND_FW:
                return b'\x06'
            else:
                return b'ok\r'  # Generic OK response for other states
        else:
            response = self.serial_conn.read_until(expected_byte)[-expected_n_bytes:]
            self.debug_log("Got response:", response.hex(' ').upper())
            return response

