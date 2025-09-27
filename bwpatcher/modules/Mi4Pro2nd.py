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

from bwpatcher.core_es32 import ES32Patcher
from bwpatcher.utils import find_pattern


class Mi4pro2ndPatcher(ES32Patcher):
    def __init__(self, data):
        super().__init__(data)

    def region_free(self):
        res = []

        sig = [0x9c, 0xa7, 0x00, 0x00, 0x22, 0x03, 0x00, 0x20]
        ofs = find_pattern(self.data, sig)
        for i in range(7):
            ofs += 4
            pre = self.data[ofs:ofs+4]
            post = b'\x21\x03\x00\x20'
            self.data[ofs:ofs+4] = post
            res += [(f"region_free_{i}", hex(ofs), pre.hex(), post.hex())]

        sig = [0x60, 0x8b, 0x60, 0x82, 0x56, 0x48, 0x00, 0x78]
        ofs = find_pattern(self.data, sig) + len(sig)
        pre = self.data[ofs:ofs+2]
        post = self.assembly("cmp r0,#0xff")
        self.data[ofs:ofs+2] = post
        res += [("region_free_fix", hex(ofs), pre.hex(), post.hex())]

        return res

    def speed_limit_drive(self, speed):
        res = []

        sig = [0x38, 0x00, 0x39, 0x01, 0xA1, 0x01, 0x39, 0x01, 0x39]
        ofs = find_pattern(self.data, sig)
        post = self._calc_speed(speed)
        for i in range(11):
            ofs += 2
            pre = self.data[ofs:ofs+2]
            self.data[ofs:ofs+2] = post
            res += [(f"speed_limit_drive_{i}", hex(ofs), pre.hex(), post.hex())]

        return res

    def speed_limit_sport(self, speed):
        res = []

        sig = [0x00, 0x00, 0xa1, 0x01, 0x0a, 0x02, 0xa1, 0x01]
        ofs = find_pattern(self.data, sig)
        post = self._calc_speed(speed)
        for i in range(11):
            ofs += 2
            pre = self.data[ofs:ofs+2]
            self.data[ofs:ofs+2] = post
            res += [(f"speed_limit_sport_{i}", hex(ofs), pre.hex(), post.hex())]

        return res

    def remove_speed_limit_sport(self):
        return self.speed_limit_sport(speed=36.7)
