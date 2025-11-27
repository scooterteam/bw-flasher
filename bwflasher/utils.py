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

from io import BytesIO
import zipfile
import fasttea

def find_pattern_offsets(pattern_hex, binary_data, start_offset=0):
    offsets = []
    if not pattern_hex:
        return offsets

    pattern = bytes.fromhex(pattern_hex)

    offset = binary_data.find(pattern, start_offset)
    while offset != -1:
        offsets.append(offset)
        offset = binary_data.find(pattern, offset + 1)

    return offsets


def _decode_model(data: bytes):
    """Tries to decode the model id from the firmware data."""
    id_ = None
    try:
        id_ = data[0x100:0x10f].decode('ascii')
    except (UnicodeDecodeError, IndexError):
        try:
            id_ = data[0x400:0x40e].decode("ascii")
        except (UnicodeDecodeError, IndexError):
            pass
    return id_


def process_firmware(firmware_data: bytes) -> bytes:
    """
    Extracts and decrypts firmware from a ZIP archive if necessary.
    This is based on the logic from the old Zippy.try_extract method.
    """
    processed_fw = firmware_data
    try:
        with zipfile.ZipFile(BytesIO(firmware_data), 'r') as zf:
            file_list = zf.namelist()
            if not file_list:
                raise ValueError("The ZIP file is empty.")

            # Find the file to extract, preferring specific filenames
            esc_file = next(
                (name for name in file_list if name.startswith('EC_ESC_Driver') or name.endswith(".enc")),
                file_list[0]
            )
            processed_fw = zf.read(esc_file)
    except zipfile.BadZipFile:
        # Not a zip file, use the raw data.
        pass

    # Decryption logic, similar to Zippy's
    if not _decode_model(processed_fw):
        try:
            decrypted_fw = fasttea.decrypt(processed_fw)
            if _decode_model(decrypted_fw):
                processed_fw = decrypted_fw
        except Exception:
            # Keep original data if decryption fails
            pass

    if len(processed_fw) > 4096:
        processed_fw = processed_fw[:-2]

    return processed_fw


def load_and_process_firmware(firmware_file_path: str) -> bytes:
    """
    Loads a firmware file, extracts it from a ZIP if necessary,
    and decrypts it if it appears to be encrypted.
    """
    try:
        with open(firmware_file_path, 'rb') as f:
            raw_data = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Firmware file not found: {firmware_file_path}")

    return process_firmware(raw_data)

# TODO: move this to tests/
def test_find_pattern_offsets():
    binary_data = b'\x00\x01\x02\x03\x04\x01\x02\x03\x04\x05'
    pattern_hex = '010203'
    expected_offsets = [1, 5]
    assert find_pattern_offsets(pattern_hex, binary_data) == expected_offsets

    expected_offsets = [5]
    assert find_pattern_offsets(pattern_hex, binary_data, start_offset=3) == expected_offsets

    pattern_hex = '0405'
    expected_offsets = [8]
    assert find_pattern_offsets(pattern_hex, binary_data) == expected_offsets

    pattern_hex = '0607'
    expected_offsets = []
    assert find_pattern_offsets(pattern_hex, binary_data) == expected_offsets

    pattern_hex = ''
    expected_offsets = []
    assert find_pattern_offsets(pattern_hex, binary_data) == expected_offsets

    binary_data = b''
    pattern_hex = '010203'
    expected_offsets = []
    assert find_pattern_offsets(pattern_hex, binary_data) == expected_offsets

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Search for a pattern in a binary file.')
    parser.add_argument('file_path', type=str, help='Path to the binary file')
    parser.add_argument('pattern_hex', type=str, help='Hexadecimal pattern to search for')

    args = parser.parse_args()

    with open(args.file_path, 'rb') as file:
        file_data = file.read()

    for offset in find_pattern_offsets(args.pattern_hex, file_data):
        print(hex(offset))


if __name__ == "__main__":
    test_find_pattern_offsets()
    main()
