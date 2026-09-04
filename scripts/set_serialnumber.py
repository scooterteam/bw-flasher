#!/usr/bin/env python3
"""
Set scooter serial number on LEQI scooters (CLI wrapper).

The serial is the scooter product serial; it is stored in dashboard BLE NVM
via UART command 0x97. Prefer:

  python -m bwflasher set-serial SERIAL --port /dev/ttyUSB0
"""

import argparse
import sys

from bwflasher.serial_number import (
    SERIAL_NUMBER_LENGTH,
    generate_serial_packet_hex,
    list_serial_ports,
    send_serial_command,
    validate_serial_number,
)


def main():
    parser = argparse.ArgumentParser(
        description="Set scooter serial number (LEQI only; stored in dashboard BLE NVM)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /dev/ttyUSB0 "0539370000000ABCDEF"
  %(prog)s /dev/ttyUSB0 "0537770000000123456" -v
  %(prog)s --generate "0539370000000ABCDEF"
  %(prog)s --list

Notes:
  - Serial number must be exactly 19 ASCII characters
  - LEQI only; Brightway/Ninebot are not supported via this command
  - Prefer: python -m bwflasher set-serial SERIAL --port PORT
        """,
    )

    parser.add_argument("port", nargs="?", help="Serial port (e.g., /dev/ttyUSB0 or COM3)")
    parser.add_argument("serial", nargs="?", help=f"{SERIAL_NUMBER_LENGTH}-character serial number")
    parser.add_argument("-b", "--baudrate", type=int, default=19200, help="Baud rate (default: 19200)")
    parser.add_argument("-t", "--timeout", type=float, default=2.0, help="Response timeout in seconds")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("-l", "--list", action="store_true", help="List available serial ports")
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Simulate set-serial without opening the serial port",
    )
    parser.add_argument(
        "-g",
        "--generate",
        metavar="SERIAL",
        help="Generate packet hex without sending",
    )

    args = parser.parse_args()

    if args.list:
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found.")
            return 1
        print("\nAvailable Serial Ports:")
        for device, description in ports:
            print(f"  {device}: {description}")
        return 0

    if args.generate:
        success, hex_string, message = generate_serial_packet_hex(args.generate)
        if success:
            print(f"\nPacket for serial '{args.generate}':")
            print(f"  {hex_string}")
            return 0
        print(f"\nERROR: {message}")
        return 1

    # With --simulation, allow a single positional as the serial:
    #   set_serialnumber.py --simulation "0539..."
    if args.simulation and args.port and not args.serial and len(args.port) == SERIAL_NUMBER_LENGTH:
        args.serial = args.port
        args.port = "SIM"

    if not args.serial or (not args.simulation and not args.port):
        parser.print_help()
        return 1

    if args.simulation and not args.port:
        args.port = "SIM"

    try:
        validate_serial_number(args.serial)
    except ValueError as e:
        print(f"\nERROR: {e}")
        return 1

    print(f"\nSetting scooter serial number to: {args.serial}")
    if args.simulation:
        print("Simulation mode: no serial I/O")
    else:
        print(f"Connecting to {args.port} @ {args.baudrate} baud...")

    success, resp_serial, message = send_serial_command(
        args.port,
        args.serial,
        baudrate=args.baudrate,
        timeout=args.timeout,
        debug_callback=print if (args.verbose or args.simulation) else None,
        simulation=args.simulation,
    )

    if success:
        print(f"\nSUCCESS: Scooter serial set to '{resp_serial}'")
        return 0

    print(f"\nFAILED: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
