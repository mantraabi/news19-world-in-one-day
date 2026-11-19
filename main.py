#!/usr/bin/env python3
"""Deliver the committed, authoring-time artwork with the Python standard library only.

The page itself is rendered by ``tools/render.py`` (Pillow, authoring time) and the
resulting ``entry.png`` is committed to this repository. The graded run must not
depend on anything outside the standard library, so this entrypoint only validates
the committed bytes by hand and copies them to the output directory.
"""
from pathlib import Path
import os
import struct
import zlib

SIZE = 1024
LIMIT = 1048576


def validated_png(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected a PNG file signature')
    if len(data) > LIMIT:
        raise ValueError('Expected a PNG of at most 1 MiB')
    position = 8
    kinds = []
    compressed = bytearray()
    expected_scanline_bytes = 0
    while position < len(data):
        if position + 12 > len(data):
            raise ValueError('Truncated PNG chunk header')
        length = struct.unpack_from('>I', data, position)[0]
        kind = data[position + 4:position + 8]
        end = position + 12 + length
        if end > len(data):
            raise ValueError('Truncated chunk')
        payload = data[position + 8:position + 8 + length]
        checksum = struct.unpack_from('>I', data, position + 8 + length)[0]
        if zlib.crc32(kind + payload) & 0xffffffff != checksum:
            raise ValueError('Invalid PNG checksum')
        if kind == b'IHDR':
            if length != 13:
                raise ValueError('Invalid PNG header length')
            width, height, depth, color, compression, filtering, interlace = struct.unpack(
                '>IIBBBBB', payload
            )
            if (width, height) != (SIZE, SIZE):
                raise ValueError('Expected a {0}x{0} image, found {1}x{2}'.format(SIZE, width, height))
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError('Expected non-interlaced eight-bit RGB artwork')
            expected_scanline_bytes = height * (1 + width * 3)
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'IEND' and length:
            raise ValueError('Invalid PNG end marker')
        kinds.append(kind)
        position = end
        if kind == b'IEND':
            break
    if not kinds or kinds[0] != b'IHDR' or kinds[-1] != b'IEND' or b'IDAT' not in kinds:
        raise ValueError('Incomplete PNG')
    if position != len(data):
        raise ValueError('Trailing bytes after the PNG end marker')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(bytes(compressed), expected_scanline_bytes + 1)
    if len(raw) != expected_scanline_bytes or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid PNG image stream')
    stride = 1 + SIZE * 3
    if any(raw[offset] > 4 for offset in range(0, len(raw), stride)):
        raise ValueError('Invalid PNG row filter')
    return data


def main():
    artwork = validated_png(Path(__file__).with_name('entry.png').read_bytes())
    destination = Path(os.environ.get('MAKEFUN_OUTPUT_DIR', '/output'))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / 'entry.png').write_bytes(artwork)


if __name__ == '__main__':
    main()
