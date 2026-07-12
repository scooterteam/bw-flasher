#!/usr/bin/env python3
"""
Product Serial Number Setter for BLE Firmware

Sends command 0x97 to set the product serial number on the dashboard BLE module.
The serial number is a 19-character ASCII string stored in BLE firmware NVM.

Command 0x97 is handled by the BLE firmware (RTL8762C), NOT the motor controller.
It writes to RAM offset 0x2d0 and persists to NVM via save_params_to_nvm(1).

Protocol:
- Baud rate: 19200, 8N1
- Packet format: [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN_LEN-byte serial] [CRC_H] [CRC_L]
- Response: [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN_LEN-byte serial] [CRC_H] [CRC_L]

Based on reverse-engineered BLE firmware analysis.
See doc/12-ble-firmware.md for detailed documentation.
"""

import serial
import serial.tools.list_ports
import argparse
import sys
import time


def calculate_crc16(data):
    """
    Calculate CRC-16 checksum used by motor controller firmware.

    This is CRC-16/XMODEM (polynomial 0x1021, init 0x0000).
    Matches the firmware's calculateCrc function.

    Args:
        data: bytes or bytearray to calculate CRC for

    Returns:
        16-bit CRC value
    """
    crc = 0x0000

    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF

    return crc


def build_serial_packet(serial_number):
    """
    Build command 0x97 packet to set product serial number.

    Packet format:
    [0x5A] [0x12] [0x97] [SN_LEN+1] [0x30] [SN_LEN-byte serial] [CRC_H] [CRC_L]

    Args:
        serial_number: ASCII string (length >= 1, typically 19)

    Returns:
        bytes: Complete packet ready to transmit

    Raises:
        ValueError: If serial number is not a non-empty string
    """
    # Validate serial number
    if not isinstance(serial_number, str):
        raise ValueError("Serial number must be a string")

    sn_len = len(serial_number)
    if sn_len == 0:
        raise ValueError("Serial number must not be empty")

    # Ensure all characters are ASCII
    try:
        serial_bytes = serial_number.encode('ascii')
    except UnicodeEncodeError as e:
        raise ValueError(f"Serial number must contain only ASCII characters: {e}")

    # Build packet without CRC
    packet = bytearray([
        0x5A,           # Header
        0x12,           # Command (0x12 = immediate processing)
        0x97,           # Subcommand (set product serial)
        sn_len + 1,     # Length: SN_LEN + 1 (for 0x30)
        0x30,           # Field after length
    ])
    packet.extend(serial_bytes)

    # Calculate and append CRC
    crc = calculate_crc16(packet)
    packet.append((crc >> 8) & 0xFF)  # CRC high byte
    packet.append(crc & 0xFF)         # CRC low byte

    return bytes(packet)


def parse_response(data):
    """
    Parse command 0x97 response packet.

    Expected format:
    [0x5A] [0x12] [0x97] [SN_LEN+1] [SN_LEN-byte serial] [CRC_H] [CRC_L]

    Args:
        data: bytes received from serial port

    Returns:
        tuple: (success, serial_number, message)
    """
    if len(data) < 7:
        return False, None, f"Response too short: {len(data)} bytes (expected at least 7)"

    # Check header
    if data[0] != 0x5A:
        return False, None, f"Invalid header: 0x{data[0]:02X} (expected 0x5A)"

    # Check response command (should be 0x12)
    if data[1] != 0x12:
        return False, None, f"Invalid response command: 0x{data[1]:02X} (expected 0x12)"

    # Check subcommand
    if data[2] != 0x97:
        return False, None, f"Invalid subcommand: 0x{data[2]:02X} (expected 0x97)"

    # Length
    sn_len = data[3]
    if sn_len < 2:
        return False, None, f"Invalid length: {sn_len_plus1} (must be >=2)"

    expected_len = 4 + sn_len + 1  # header+cmd+subcmd+len + serial + CRC
    if len(data) < expected_len:
        return False, None, f"Response too short: {len(data)} bytes (expected {expected_len})"

    # Extract serial number
    try:
        serial_number = data[4:4+sn_len].decode('ascii')
    except UnicodeDecodeError:
        return False, None, "Response contains non-ASCII serial number"

    # CRC check
    crc_received = (data[4+sn_len] << 8) | data[4+sn_len+1]
    crc_calculated = calculate_crc16(data[:4+sn_len])
    if crc_received != crc_calculated:
        return False, serial_number, f"CRC mismatch: got 0x{crc_received:04X}, expected 0x{crc_calculated:04X}"

    return True, serial_number, "OK"


def list_serial_ports():
    """List available serial ports."""
    ports = serial.tools.list_ports.comports()
    return [(p.device, p.description) for p in ports]


def read_response(ser, timeout=2.0, verbose=False):
    """
    Read and parse a response packet from the controller.

    Args:
        ser: Serial port object
        timeout: Response timeout in seconds
        verbose: Enable verbose logging

    Returns:
        bytes: Response packet (empty if timeout/error)
    """
    response = bytearray()
    start_time = time.time()

    # Look for header byte (0x5A)
    while time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            byte = ser.read(1)
            if byte[0] == 0x5A:
                response.append(byte[0])
                if verbose:
                    print(f"[RX] Found header byte 0x5A")
                break
        time.sleep(0.01)

    if len(response) == 0:
        if verbose:
            print(f"[RX] No response (timeout)")
        return bytes()

    # Read next 4 bytes: [cmd][subcmd][len][0x30]
    needed = 4
    while needed > 0 and time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(min(needed, ser.in_waiting))
            response.extend(chunk)
            needed -= len(chunk)
        time.sleep(0.01)

    if len(response) < 5:
        if verbose:
            print(f"[RX] Incomplete response header")
        return bytes(response)

    # Now determine SN_LEN from length field
    sn_len_plus1 = response[3]
    sn_len = sn_len_plus1 - 1
    total_len = 5 + sn_len + 2  # header+cmd+subcmd+len+0x30 + serial + CRC

    # Read remaining bytes
    remaining = total_len - len(response)
    while remaining > 0 and time.time() - start_time < timeout:
        if ser.in_waiting > 0:
            chunk = ser.read(min(remaining, ser.in_waiting))
            response.extend(chunk)
            remaining -= len(chunk)
        time.sleep(0.01)

    if verbose:
        print(f"[RX] Response ({len(response)} bytes): {' '.join(f'{b:02X}' for b in response)}")

    return bytes(response)


def send_serial_command(port, serial_number, baudrate=19200, timeout=2.0, verbose=False, max_attempts=10):
    """
    Send command 0x97 to set product serial number, read up to max_attempts responses, and return on first valid match.

    Args:
        port: Serial port path (e.g., '/dev/ttyUSB0' or 'COM3')
        serial_number: 19-character ASCII serial number string
        baudrate: Baud rate (default: 19200)
        timeout: Response timeout in seconds
        verbose: Enable verbose logging
        max_attempts: Number of responses to read (default: 10)

    Returns:
        tuple: (success, response_serial, message)
    """
    try:
        packet = build_serial_packet(serial_number)
    except ValueError as e:
        return False, None, str(e)

    if verbose:
        print(f"[TX] Packet ({len(packet)} bytes): {' '.join(f'{b:02X}' for b in packet)}")
        print(f"     Header: 0x{packet[0]:02X}")
        print(f"     Command: 0x{packet[1]:02X} (immediate)")
        print(f"     Subcommand: 0x{packet[2]:02X} (set serial)")
        print(f"     Length: 0x{packet[3]:02X} ({packet[3]} bytes)")
        print(f"     Serial: {serial_number}")
        print(f"     CRC: 0x{packet[23]:02X}{packet[24]:02X}")

    errors = []
    try:
        # Open serial port
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout
        )

        if verbose:
            print(f"\n[INFO] Serial port opened: {port} @ {baudrate} baud")

        # Flush buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Send packet
        ser.write(packet)
        if verbose:
            print(f"[INFO] Sent {len(packet)} bytes")
            print(f"[INFO] Waiting for response(s)...")

        # Try up to max_attempts to get a valid response
        for attempt in range(max_attempts):
            response = read_response(ser, timeout, verbose)
            if len(response) == 0:
                msg = f"Timeout waiting for response {attempt+1}"
                errors.append((False, None, msg))
                if verbose:
                    print(f"[ERROR] {msg}")
                continue

            success, resp_serial, message = parse_response(response)
            if success and resp_serial == serial_number:
                if verbose:
                    print(f"\n[OK] Response {attempt+1}: Serial number set successfully")
                    print(f"     Response serial: {resp_serial}")
                ser.close()
                return True, resp_serial, "OK"
            else:
                errors.append((success, resp_serial, message))
                if verbose:
                    print(f"\n[ERROR] Response {attempt+1}: {message}")

        ser.close()
        # If none matched, return the first error (or last)
        if errors:
            return errors[0]
        else:
            return False, None, "No valid response received"

    except serial.SerialException as e:
        return False, None, f"Serial error: {e}"
    except Exception as e:
        return False, None, f"Unexpected error: {e}"


def generate_serial_packet_hex(serial_number):
    """
    Generate hex packet string without sending.

    Args:
        serial_number: 19-character ASCII serial number string

    Returns:
        tuple: (success, hex_string, message)
    """
    try:
        packet = build_serial_packet(serial_number)
        hex_string = ' '.join(f'{b:02X}' for b in packet)
        return True, hex_string, "OK"
    except ValueError as e:
        return False, None, str(e)


def main():
    parser = argparse.ArgumentParser(
        description="Set product serial number on BLE firmware (command 0x97)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Set serial number via UART
  %(prog)s /dev/ttyUSB0 "0539370000000ABCDEF"

  # Set serial number with verbose output
  %(prog)s /dev/ttyUSB0 "0537770000000123456" -v

  # Generate packet hex without sending
  %(prog)s --generate "0539370000000ABCDEF"

  # List available serial ports
  %(prog)s --list

Notes:
  - Serial number must be exactly 19 ASCII characters
  - Common format: 9 digits + 10 alphanumeric characters
  - Examples: "0539370000000ABCDEF", "0537770000000123456"
  - Command is handled by BLE firmware (RTL8762C), not motor controller
  - Serial number is persisted to NVM and exposed via Xiaomi MIoT protocol
        """
    )

    parser.add_argument('port', nargs='?', help='Serial port (e.g., /dev/ttyUSB0 or COM3)')
    parser.add_argument('serial', nargs='?', help='19-character serial number string')
    parser.add_argument('-b', '--baudrate', type=int, default=19200,
                        help='Baud rate (default: 19200)')
    parser.add_argument('-t', '--timeout', type=float, default=2.0,
                        help='Response timeout in seconds (default: 2.0)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List available serial ports')
    parser.add_argument('-g', '--generate', metavar='SERIAL',
                        help='Generate packet hex without sending (for testing/BLE)')

    args = parser.parse_args()

    # Handle --list
    if args.list:
        ports = list_serial_ports()
        if not ports:
            print("No serial ports found.")
            return 1

        print("\nAvailable Serial Ports:")
        for device, description in ports:
            print(f"  {device}: {description}")
        return 0

    # Handle --generate
    if args.generate:
        success, hex_string, message = generate_serial_packet_hex(args.generate)
        if success:
            print(f"\nPacket for serial '{args.generate}':")
            print(f"  {hex_string}")
            print(f"\nPacket breakdown:")
            packet = bytearray.fromhex(hex_string.replace(' ', ''))
            print(f"  Header:     0x{packet[0]:02X}")
            print(f"  Command:    0x{packet[1]:02X} (immediate)")
            print(f"  Subcommand: 0x{packet[2]:02X} (set serial)")
            print(f"  Length:     0x{packet[3]:02X} ({packet[3]} bytes)")
            print(f"  Serial:     {args.generate}")
            print(f"  CRC:        0x{packet[23]:02X}{packet[24]:02X}")
            return 0
        else:
            print(f"\n✗ ERROR: {message}")
            return 1

    # Require port and serial for actual operation
    if not args.port or not args.serial:
        parser.print_help()
        return 1

    # Validate serial number length
    if len(args.serial) != 19:
        print(f"\n✗ ERROR: Serial number must be exactly 19 characters (got {len(args.serial)})")
        print(f"  Your input: '{args.serial}'")
        return 1

    print(f"\nSetting product serial number to: {args.serial}")
    print(f"Connecting to {args.port} @ {args.baudrate} baud...")

    # Send command and read up to 10 responses, succeed if any matches
    success, resp_serial, message = send_serial_command(
        args.port,
        args.serial,
        baudrate=args.baudrate,
        timeout=args.timeout,
        verbose=args.verbose,
        max_attempts=10
    )

    if success:
        print(f"\n✓ SUCCESS: Serial number set to '{resp_serial}'")
        return 0
    else:
        print(f"\n✗ FAILED: {message}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
