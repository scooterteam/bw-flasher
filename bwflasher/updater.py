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

import requests
from platform import python_version
from bwflasher import __version__

BWFLASHER_RELEASES = "https://api.github.com/repos/scooterteam/bw-flasher/releases"
REQUESTS_HEADERS = {
    'User-Agent': f'BWFlasher/{__version__} Python/{python_version()} python-requests/{requests.__version__}'
}


def get_name():
    return f"BWFlasher v{__version__}"


def check_update() -> dict:
    gh_req = requests.get(BWFLASHER_RELEASES, headers=REQUESTS_HEADERS, timeout=3)
    if gh_req.status_code != 200:
        return {}

    gh_json = gh_req.json()[0]
    if gh_json['tag_name'].strip('v') > __version__:
        return gh_json

    return {}

