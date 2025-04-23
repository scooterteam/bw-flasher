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

def print_array(arr):
    print(' '.join(f'{x:02X}' for x in arr[:16]))


def gen_key(dst, src, lookup_table_0, lookup_table_1):
    """Generate the key from UID and lookup tables."""
    dst[:16] = src[:16]

    local = bytearray([0, 0, 0, 0])
    # keep first 16 bytes as they are
    for j in range(16, 176, 4):
        # copy first 4 bytes of previous block
        dst[j:j+4] = dst[j-16:j-12]

        # add entropy from last 4 bytes of previous block
        if (j % 16) != 0:
            # use copy of last bytes
            local[:4] = dst[j-4:j]
        else:
            # every 16 bytes, use last bytes with substitution
            local[:4] = [
                lookup_table_0[dst[j - 3]] ^ lookup_table_1[j // 16],
                lookup_table_0[dst[j - 2]],
                lookup_table_0[dst[j - 1]],
                lookup_table_0[dst[j - 4]],
            ]
        # XORing
        for i in range(4):
            dst[j + i] ^= local[i]


def xor_byte_blocks(dst, src, block_index):
    """XOR 4-byte blocks from two arrays."""
    for j in range(block_index * 16, (block_index + 1) * 16):
        dst[j % 16] ^= src[j]


def manipulate_bytes(dst_src, c=-0x1b):
    """ Irreversible byte mutation (in-place). """
    def to_char(byte):
        return byte if byte < 128 else byte - 256

    def get_sign(byte):
        return byte >> 7  # return -1 if to_char(byte) < 0 else 0

    local = [0, 0, 0, 0, 0]
    for offset in range(0, 16, 4):
        local[0] = dst_src[offset] ^ dst_src[offset + 1]
        local[1] = dst_src[offset + 1] ^ dst_src[offset + 2]
        local[2] = dst_src[offset + 2] ^ dst_src[offset + 3]
        local[3] = dst_src[offset + 3] ^ dst_src[offset + 0]
        local[4] = local[0] ^ local[2]

        for i in range(4):
            dst_src[offset + i] ^= (local[i] << 1) & 0xFF
            dst_src[offset + i] ^= get_sign(to_char(local[i])) * c
            dst_src[offset + i] ^= local[4]


def roll_bytes(bytearr, indices):
    # Extract the values at the given indices
    values = [bytearr[i] for i in indices]

    # Roll the values to the next position
    rolled_values = values[1:] + values[:1]

    # Assign the rolled values back to the bytearray
    for i, index in enumerate(indices):
        bytearr[index] = rolled_values[i]


def sign_rand_with_key(dst, src, lookup_table):
    """ Main function. """
    for current_block in range(0, 10):
        if current_block > 0:
            manipulate_bytes(dst)
        xor_byte_blocks(dst, src, current_block)

        # Transform dst_array with lookup table and rotation
        for outer_index in range(0, 16, 4):
            for inner_index in range(4):
                table_index = dst[inner_index + outer_index]
                dst[inner_index + outer_index] = lookup_table[table_index]

        # Rotate the bytes
        roll_bytes(dst, [1, 5, 9, 13])
        roll_bytes(dst, [2, 10])
        roll_bytes(dst, [3, 15, 11, 7])
        roll_bytes(dst, [6, 14])

    # Final XOR operation
    xor_byte_blocks(dst, src, 10)


def sign_rand(
    uid: bytearray(16),
    rand: bytearray(16),
    fw: bytes,
    base_offset: int = 0x17080
):
    """
    Sign challenge `rand` with key generated from `uid`,
    using tables from `fw`.
    """
    lookup_table_0 = bytearray(256)
    for i in range(256):
        lookup_table_0[i] = fw[base_offset+0xA802+i]

    lookup_table_1 = bytearray(1+10)
    for i in range(1, 1+10):  # byte0 is not used
        lookup_table_1[i] = fw[base_offset+0xAA02+i]

    key = bytearray(176)
    gen_key(key, uid, lookup_table_0, lookup_table_1)

    dst = bytearray(rand)
    sign_rand_with_key(dst, key, lookup_table_0)

    return dst


if __name__ == "__main__":
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("uid")
    parser.add_argument("rand")
    parser.add_argument("fw")
    parser.add_argument("--fw-base-offset", default=0x17080)
    args = parser.parse_args()

    fw = None
    with open(args.fw, 'rb') as f:
        fw = f.read()

    key = sign_rand(
        args.uid.encode(),
        bytes.fromhex(args.rand),
        fw,
        base_offset=args.fw_base_offset
    )
    print(key.hex())
