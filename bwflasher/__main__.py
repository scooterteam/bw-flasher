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

import os

from bwflasher.firmware_detector import create_flasher_for_firmware

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

        updater = create_flasher_for_firmware(
            firmware_file=args.fw_file,
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
