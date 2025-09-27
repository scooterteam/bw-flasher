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

import crcmod

from bwpatcher.core import CorePatcher
from bwpatcher.utils import find_pattern

class ES32Patcher(CorePatcher):
    def __init__(self, data):
        super().__init__(data)

    @classmethod
    def _calc_speed(cls, speed, factor=20.9, size=2):
        if size == 0:
            return int(factor * speed)
        return int(factor * speed).to_bytes(size, 'little')

    def fix_checksum(self):
        sig = 'SZMC-ES-ZM-'.encode()
        ofs_ = find_pattern(self.data, sig)

        ofs = ofs_ + 0x20
        size = int.from_bytes(
            self.data[ofs-0x2a:ofs-0x28],
            byteorder='big'
        )
        pre = self.data[ofs:ofs+2]
        post = CorePatcher._compute_checksum(
            self.data,
            offset=ofs+0x50,
            size=size
        )
        assert len(post) == 2
        self.data[ofs:ofs+2] = post[:2]

        ofs = ofs_ - 0x10
        res = super().fix_checksum(ofs)
        return [("fix_checksum", hex(ofs), pre.hex(), post.hex()), res]

    def cruise_control_enable(self):
        sig = [0xca, 0x09, 0x1a, 0x70, 0x4a, 0x06, None, 0x4b, 0xd2, 0x0f, 0x1a, 0x70, 0x8a, 0x06, None, 0x4b, 0xd2, 0x0f, 0x1a, 0x70]
        ofs = find_pattern(self.data, sig) + len(sig) - 4
        pre = self.data[ofs:ofs+2]
        post = self.assembly("movs r2,#0x1")
        self.data[ofs:ofs+2] = post
        return [("cruise_control_enable", hex(ofs), pre.hex(), post.hex())]

    def motor_start_speed(self, kmh):
        res = []

        sigs = [
            [0x00, 0x99, 0x68, 0x29, 0x0e, 0xdb, 0x9a, 0x49, 0x09, 0x78, 0x01, 0x29, 0x09, 0xd0, 0x09, 0xe0],
            [0x00, 0x99, 0x3e, 0x29, 0x01, 0xda, 0xc4, None, 0xf8, 0xe7]
        ]

        speed_min = self._calc_speed(1, size=0)
        for i, sig in enumerate(sigs):
            speed = self._calc_speed(kmh, size=0)
            if i == 1:
                speed = (speed + speed_min) // 2  # hysteresis

            ofs = find_pattern(self.data, sig) + 2
            pre = self.data[ofs:ofs+2]
            post = self.assembly(f"cmp r1,#{speed}")
            self.data[ofs:ofs+2] = post

            res += [(f"motor_start_speed_{i}", hex(ofs), pre.hex(), post.hex())]

        return res
