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

from bwpatcher.modules.Mi5 import Mi5Patcher
from bwpatcher.utils import find_pattern


class Mi5maxPatcher(Mi5Patcher):
    SNS = [(0x85, 0xEC, 0x0, 0x0), (0xC4, 0xEE, 0x0, 0x0)]
    SIG_CCU = [0x13, 0x68, 0x93, 0x4d, 0xab, 0x42, 0x1e, 0xd0, 0x12, 0x68, 0x92, 0x4b, 0x9a, 0x42, 0x1a, 0xd0]#, 0x62, 0x7a, 0x91, 0x4e, 0x00, 0x2a, 0x0e, 0xd0 ]

    def __init__(self, data):
        super().__init__(data)