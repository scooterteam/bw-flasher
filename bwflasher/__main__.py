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

import os

from bwflasher.flash_uart import DFU


def main():
    import argparse
    from tqdm import tqdm

    default_port = "COM1" if os.name == "nt" else "/dev/ttyUSB0"
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("fw_file")
    parser.add_argument("--simulation", action='store_true')
    parser.add_argument("--debug", action='store_true', help="Enable debug output")
    parser.add_argument("--port", default=default_port, help="Serial port")
    args = parser.parse_args()

    with tqdm(total=100, desc="Flashing") as pbar:
        def log_callback(message):
            tqdm.write(message)

        def status_callback(status):
            tqdm.write(status)

        def progress_callback(progress):
            pbar.n = progress
            pbar.refresh()

        updater = DFU(
            tty_port=args.port,
            simulation=args.simulation,
            debug=args.debug,
            log_callback=log_callback,
            status_callback=status_callback,
            progress_callback=progress_callback
        )
        updater.load_file(args.fw_file)

        updater.run()


if __name__ == "__main__":
    main()
