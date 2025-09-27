#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Patcher
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

import math
import crcmod

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern, SignatureException


class LKS32Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    def _branch_from_to(self, sig: list, sig_dst: list, description: str, dst_offset: int = 4):
        # TODO: offsets from src and dst are really weird, need to fix it
        ret = []
        ofs = find_pattern(self.data, sig) + len(sig)
        # jump to the end of the function
        ofs_dst = find_pattern(self.data, sig_dst, start=ofs) + dst_offset
        pre = self.data[ofs:ofs+2]
        post = self.assembly(f"b {ofs_dst-ofs}")
        if pre != post:
            self.data[ofs:ofs+2] = post
            ret.append((description, hex(ofs), pre.hex(), post.hex()))
        return ret

    @staticmethod
    def _safe_ldr(ldr_offset: int, dst_ofs: int) -> tuple[int, int]:
        pc_base = (ldr_offset & ~0x3) + 4
        min_off = dst_ofs - pc_base
        if min_off < 0:
            raise ValueError("Minimum destination offset is earlier than PC_base")
        if min_off % 4 != 0:
            min_off = (min_off & ~0x3) + 4

        ldr_ofs_val = int(math.ceil(min_off / 4.0))
        return pc_base + (ldr_ofs_val * 4), min_off

    @classmethod
    def _compute_checksum(cls, data, offset, size):
        if size > len(data):
            raise Exception("Error: File is shorter than expected range.")

        data = data[offset:offset+size]

        # pad with 0xFF to make data length a multiple of 4
        pad_len = (-len(data)) % 4
        padded = data + b'\xFF' * pad_len

        # create a CRC-32 function to simulate hardware CRC unit
        crc_func = crcmod.mkCrcFun(0x104C11DB7, initCrc=0xFFFFFFFF, rev=False)

        chk = crc_func(padded) & 0xFFFFFFFF
        return chk.to_bytes(4, byteorder='little')

    def _cruise_control_unlock(self):
        if not hasattr(self, "SIG_CCU"):
            return []

        sig = self.SIG_CCU
        ofs = find_pattern(self.data, sig)
        pre = self.data[ofs:ofs+len(sig)]
        post = self.assembly('nop') * (len(sig) // 2)
        assert len(pre) == len(post)
        self.data[ofs:ofs+len(sig)] = post
        return ("cruise_control_unlock", hex(ofs), pre.hex(), post.hex())

    def _calc_speed(self, kmh, factor=10, size=4):
        if size == 0:
            return int(kmh*factor)

        return int(kmh*factor).to_bytes(size, byteorder='little')

    def fix_checksum(self):
        sig = 'LKS32MC0'.encode()
        ofs = find_pattern(self.data, sig) - 0x8

        if self.data[ofs-2:ofs] != b'\xFF\xFF':
            return

        size = int.from_bytes(
            self.data[ofs:ofs+4],
            byteorder='little'
        )
        pre = self.data[ofs+4:ofs+8]
        post = LKS32Patcher._compute_checksum(
            self.data,
            offset=ofs+0x18,
            size=size
        )
        assert len(post) == 4
        self.data[ofs+4:ofs+8] = post

        res = super().fix_checksum(ofs)
        return [("fix_checksum", hex(ofs), pre.hex(), post.hex()), res]

    def fake_drv_version(self, firmware_version: str):
        if not firmware_version.isdigit():
            raise ValueError(f"Firmware version must contain only digits: {firmware_version}")
        if len(firmware_version) != 4:
            raise ValueError(f"Firmware version must have 4 digits: {firmware_version}")

        sig = [0x6F, 0x6B, 0x0D, None, None, None, None, 0x0D, 0x65, 0x72, 0x72, 0x6F, 0x72]
        ofs = find_pattern(self.data, sig) + 3
        pre = self.data[ofs:ofs+4]
        post = firmware_version.encode("ascii")
        self.data[ofs:ofs+4] = post
        return [("fake_drv_version", hex(ofs), pre.hex(), post.hex())]

    def cruise_control_enable(self):
        res = []

        sig = [0x81, 0x06, None, 0x4b, 0xc9, 0x0f, 0x19, 0x70, 0x01, 0x07, None, 0x4b, 0xc9, 0x0f, 0x19, 0x70]
        ofs = find_pattern(self.data, sig) + 4
        pre = self.data[ofs:ofs+2]
        post = self.assembly("movs r1, #0x1")
        self.data[ofs:ofs+2] = post
        res += [("cruise_control_enable", hex(ofs), pre.hex(), post.hex())]

        res += self._cruise_control_unlock()

        return res

    def region_free(self):
        if not hasattr(self, "SNS"):
            return

        res = []
        i = 0
        for sn in self.SNS:
            ofs = 0
            while True:
                try:
                    ofs = find_pattern(self.data, sn, start=ofs+1)
                    pre = self.data[ofs:ofs+4]
                    post = b'\0\0\0\0'
                    self.data[ofs:ofs+4] = post
                    res += [(f"region_free_{i}", hex(ofs), pre.hex(), post.hex())]
                    i += 1
                except SignatureException:
                    break

        return res
