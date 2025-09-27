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

import keystone
import capstone
import crcmod

from bwpatcher.utils import find_pattern


class CorePatcher():
    def __init__(self, data):
        self.data = bytearray(data)
        self.ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_THUMB)
        self.cs = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB | capstone.CS_MODE_LITTLE_ENDIAN)

    @classmethod
    def _compute_checksum(cls, data, offset, size):
        if size > len(data):
            raise Exception("Error: File is shorter than expected range.")

        data = data[offset:offset+size]
        chk = crcmod.mkCrcFun(poly=0x11021, initCrc=0, rev=False, xorOut=0)(data)
        # alternative: chk = binascii.crc_hqx(data, 0)

        return chk.to_bytes(2, byteorder='big')

    def assembly(self, code):
        return bytes(self.ks.asm(code)[0])

    def disassembly(self, code_bytes: bytes):
        """Disassemble bytes and return code"""
        instructions = []
        for insn in self.cs.disasm(code_bytes, 0):
            instructions.append(f"{insn.mnemonic}\t{insn.op_str}")
        return "\n".join(instructions)

    def dashboard_max_speed(self, speed: float):
        raise NotImplementedError()

    def speed_limit_drive(self, kmh: float):
        raise NotImplementedError()

    def speed_limit_sport(self, kmh: float):
        raise NotImplementedError()

    def remove_speed_limit_sport(self):
        raise NotImplementedError()

    def region_free(self):
        raise NotImplementedError()

    def fake_drv_version(self, firmware_version: str):
        raise NotImplementedError()

    def motor_start_speed(self, speed: int):
        raise NotImplementedError()

    def fix_checksum(self, start_ofs):
        if self.data[start_ofs-2:start_ofs] != b'\xFF\xFF':
            return

        if chr(self.data[0]) == 'T':
            size = len(self.data) - start_ofs
            chk_ofs = 0x13
        else:
            size = int.from_bytes(
                self.data[0:0x4],
                byteorder='big'
            )
            chk_ofs = 0xa

        pre = self.data[chk_ofs:chk_ofs+2]
        while pre == b'\0\0' and chk_ofs < 0x2e:
            chk_ofs += 0x10
            pre = self.data[chk_ofs:chk_ofs+2]

        post = CorePatcher._compute_checksum(
            self.data,
            offset=start_ofs,
            size=size
        )
        assert len(post) == 2
        self.data[chk_ofs:chk_ofs+2] = post

        return ("fix_checksum_header", hex(chk_ofs), pre.hex(), post.hex())
