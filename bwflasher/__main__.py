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

import argparse
import os
import sys

from bwflasher.base_flasher import create_flasher_for_firmware
from bwflasher.serial_number import (
    SERIAL_NUMBER_LENGTH,
    list_serial_ports,
    send_serial_command,
    validate_serial_number,
)


KNOWN_COMMANDS = {"flash", "set-serial"}


def _legacy_flash_argv(argv):
    """Map legacy `bwflasher <fw_file> ...` to the flash subcommand."""
    if not argv or argv[0] in ("-h", "--help"):
        return argv
    if argv[0] in KNOWN_COMMANDS:
        return argv
    return ["flash", *argv]


def cmd_flash(args):
    from tqdm import tqdm

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
            progress_callback=progress_callback,
        )
        updater.load_file(args.fw_file)
        updater.run()
    return 0


def cmd_set_serial(args):
    if not args.serial:
        print("ERROR: serial number is required", file=sys.stderr)
        return 1

    try:
        validate_serial_number(args.serial)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Setting scooter serial number to: {args.serial}")
    if args.simulation:
        print("Simulation mode: no serial I/O")
    else:
        print(f"Connecting to {args.port} @ 19200 baud...")

    success, resp_serial, message = send_serial_command(
        port=args.port,
        serial_number=args.serial,
        timeout=args.timeout,
        debug_callback=print if (args.verbose or args.simulation) else None,
        simulation=args.simulation,
    )

    if success:
        print(f"SUCCESS: Scooter serial set to '{resp_serial}'")
        return 0

    print(f"FAILED: {message}", file=sys.stderr)
    return 1


def main(argv=None):
    default_port = "COM1" if os.name == "nt" else "/dev/ttyUSB0"
    argv = _legacy_flash_argv(list(argv if argv is not None else sys.argv[1:]))

    parser = argparse.ArgumentParser(
        prog="bwflasher",
        description="Flash scooter controllers and set LEQI scooter serial numbers",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    flash_parser = subparsers.add_parser(
        "flash",
        help="Flash firmware over UART",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    flash_parser.add_argument("fw_file")
    flash_parser.add_argument("--simulation", action="store_true")
    flash_parser.add_argument("--debug", action="store_true", help="Enable debug output")
    flash_parser.add_argument("--port", default=default_port, help="Serial port")
    flash_parser.set_defaults(func=cmd_flash)

    serial_parser = subparsers.add_parser(
        "set-serial",
        help="Set scooter serial number (LEQI only; stored in dashboard BLE NVM)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    serial_parser.add_argument(
        "serial",
        nargs="?",
        help=f"Scooter serial number ({SERIAL_NUMBER_LENGTH} ASCII characters)",
    )
    serial_parser.add_argument("--port", default=default_port, help="Serial port")
    serial_parser.add_argument(
        "-t", "--timeout", type=float, default=2.0, help="Response timeout in seconds"
    )
    serial_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    serial_parser.add_argument("--simulation", action="store_true", help="Do not open the serial port")
    serial_parser.add_argument(
        "-l", "--list", action="store_true", help="List available serial ports and exit"
    )
    serial_parser.set_defaults(func=cmd_set_serial)

    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        parser.print_help()
        return 1

    if args.command == "set-serial" and getattr(args, "list", False):
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found.")
            return 1
        print("Available Serial Ports:")
        for device, description in ports:
            print(f"  {device}: {description}")
        return 0

    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main())
