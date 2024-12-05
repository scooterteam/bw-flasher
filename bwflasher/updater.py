#!/usr/bin/env python3
#! -*- coding: utf-8 -*-
#
# BW Flasher
# Copyright (C) 2024 ScooterTeam
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
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

