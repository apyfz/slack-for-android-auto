#!/usr/bin/env python3
"""Append one XML resource without rebuilding Slack's split-aware resource table.

All original resource IDs, string indexes, configurations and resource payloads
remain intact. Only the two pools and XML entry offset tables grow. Output is
unsigned and intentionally retains original DEX; overlay patched DEX afterward.
"""
import argparse
import struct
from pathlib import Path
from zipfile import ZipFile

U32 = lambda b, o: struct.unpack_from('<I', b, o)[0]

def put(b, off, value):
    struct.pack_into('<I', b, off, value)

def chunks(b, start, end):
    while start < end:
        kind, header, size = struct.unpack_from('<HHI', b, start)
        assert size >= header >= 8 and start + size <= end
        yield start, kind, header, size
        start += size
    assert start == end

def length8(n):
    assert n < 0x8000
    return bytes([n]) if n < 128 else bytes([0x80 | (n >> 8), n & 255])

def append_string(pool, text):
    count, styles, flags, start, style_start = struct.unpack_from('<5I', pool, 8)
    assert flags & 256, 'Expected UTF-8 string pool'
    header = struct.unpack_from('<H', pool, 2)[0]
    old_data_end = style_start or len(pool)
    raw = text.encode('utf-8')
    encoded = length8(len(text.encode('utf-16le')) // 2) + length8(len(raw)) + raw + b'\0'
    encoded += bytes((-len(encoded)) % 4)
    # Insert new string offset before style offsets; original string/style bytes
    # and all their relative offsets are unchanged.
    index_end = header + count * 4
    result = bytearray(pool[:index_end] + struct.pack('<I', old_data_end - start)
                       + pool[index_end:old_data_end] + encoded + pool[old_data_end:])
    put(result, 4, len(result))
    put(result, 8, count + 1)
    put(result, 16, flags & ~1)  # append order need not remain lexicographically sorted
    put(result, 20, start + 4)
    if style_start:
        put(result, 24, style_start + 4 + len(encoded))
    return bytes(result), count

def append_xml(package, string_index):
    header = struct.unpack_from('<H', package, 2)[0]
    type_pool_offset, key_pool_offset = U32(package, 268), U32(package, 276)
    additions = []
    key_index = None
    xml_count = None
    for off, kind, hs, size in chunks(package, header, len(package)):
        part = package[off:off + size]
        if off == key_pool_offset:
            part, key_index = append_string(part, 'automotive_app_desc')
        additions.append((off, kind, hs, part))
    assert key_index is not None
    out = bytearray(package[:header])
    xml_types = 0
    for off, kind, hs, source in additions:
        if off == type_pool_offset:
            put(out, 268, len(out))
        if off == key_pool_offset:
            put(out, 276, len(out))
        part = bytearray(source)
        if kind == 0x202 and part[8] == 23:
            xml_count = U32(part, 12)
            assert xml_count == 20
            part += bytes(4)  # no configuration variation flags
            put(part, 12, xml_count + 1)
            put(part, 4, len(part))
        elif kind == 0x201 and part[8] == 23:
            assert part[9] == 0, 'Expected dense 32-bit offsets'
            assert U32(part, 12) == xml_count == 20
            assert not any(part[24:hs]), 'Expected default XML configuration only'
            entries_start = U32(part, 16)
            index_end = hs + xml_count * 4
            entry_offset = len(part) - entries_start
            part[index_end:index_end] = struct.pack('<I', entry_offset)
            # ResTable_entry(size,flags,key) then Res_value(size,res0,type,data).
            part += struct.pack('<HHIHBBI', 8, 0, key_index, 8, 0, 3, string_index)
            put(part, 12, xml_count + 1)
            put(part, 16, entries_start + 4)
            put(part, 4, len(part))
            xml_types += 1
        out += part
    assert xml_types == 1
    put(out, 4, len(out))
    return bytes(out)

def extend_table(original):
    header = struct.unpack_from('<H', original, 2)[0]
    out = bytearray(original[:header])
    string_index = None
    for off, kind, hs, size in chunks(original, header, len(original)):
        part = original[off:off + size]
        if kind == 1:
            assert string_index is None
            part, string_index = append_string(part, 'res/xml/automotive_app_desc.xml')
        elif kind == 0x200:
            assert U32(part, 8) == 0x7f and string_index is not None
            part = append_xml(part, string_index)
        out += part
    put(out, 4, len(out))
    return bytes(out)

def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, default=root / 'slack-base.apk')
    parser.add_argument('--rebuilt', type=Path, default=root / 'patched-apks/base-unsigned.apk')
    parser.add_argument('--output', type=Path, default=root / 'patched-apks/base-resource-safe.apk')
    args = parser.parse_args()
    replacements = ('AndroidManifest.xml', 'resources.arsc')
    extra = 'res/xml/automotive_app_desc.xml'
    preserved = 0
    with ZipFile(args.original) as old, ZipFile(args.rebuilt) as rebuilt, ZipFile(args.output, 'w') as out:
        assert extra not in old.namelist()
        for info in old.infolist():
            if info.filename.startswith('META-INF/') and info.filename.endswith(('.RSA', '.DSA', '.EC', '.SF', '.MF')):
                continue
            data = old.read(info.filename)
            if info.filename == 'AndroidManifest.xml':
                data = rebuilt.read(info.filename)
            elif info.filename == 'resources.arsc':
                data = extend_table(data)
            else:
                preserved += 1
            out.writestr(info, data)
        out.writestr(rebuilt.getinfo(extra), rebuilt.read(extra))
    with ZipFile(args.original) as old, ZipFile(args.output) as new:
        for name in new.namelist():
            if name not in replacements and name != extra:
                assert old.read(name) == new.read(name), name
    print(f'Wrote {args.output}; {preserved} original entries byte-identical; appended 0x7f170014.')

if __name__ == '__main__':
    main()
