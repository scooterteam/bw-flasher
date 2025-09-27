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

import argparse

from bwpatcher.modules import ALL_MODULES
from bwpatcher.utils import patch_map, patch_firmware


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("model", help="Dev name of scooter.", type=str.lower, choices=ALL_MODULES)
    parser.add_argument("infile")
    parser.add_argument("outfile")
    parser.add_argument("patches", type=str, help="The patches that are to be applied. Choose from: " + ', '.join(patch_map.keys()))
    args = parser.parse_args()

    with open(args.infile, 'rb') as fh:
        data = fh.read()

    output_data = patch_firmware(args.model, data, args.patches.split(","), web=False)
    with open(args.outfile, 'wb') as fh:
        fh.write(output_data)
