"""Restore the complete world event bank after the expanded menu uses its RAM.

The original mode-2 (Tent) path reloaded just 0x62000 of OGA_BIN.BIN. Korean
menu data extends past 0x80192000, so the untouched world-script tail was stale.
Use the original CD directory's complete file length; preserve the native read
queue, overlay decompressor and graphics initialization order.
"""
import struct

PATCHES = ((0x8003a74c, 0x3c070006, 0x8f8702f4),
           (0x8003a754, 0x34e72000, 0))


def patch(executable):
    data = bytearray(executable)
    base = struct.unpack_from('<I', data, 0x18)[0]
    for address, old, new in PATCHES:
        at = address - base + 0x800
        actual = struct.unpack_from('<I', data, at)[0]
        if actual not in (old, new):
            raise ValueError(('World partial-reload guard', hex(address), hex(actual)))
        struct.pack_into('<I', data, at, new)
    return bytes(data)
