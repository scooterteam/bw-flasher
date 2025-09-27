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

import glob

from os.path import dirname, basename, isfile


# Get all modules to import from directory
# https://stackoverflow.com/a/47473360
def _get_all_modules():
    mod_paths = glob.glob(dirname(__file__) + '/*.py')
    return [
        basename(f)[:-3] for f in mod_paths
        if isfile(f) and f.endswith('.py') and not f.endswith('__init__.py')
    ]


ALL_MODULES = sorted(_get_all_modules())
