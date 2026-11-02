#!/usr/bin/env python3
"""Darken the three version-pinned night outline tokens without rebuilding ARSC."""
import struct
from add_car_resource import chunks,U32,put

NIGHT={0x316:(0xff797c81,0xff42454a),0x317:(0x80797c81,0x8042454a),0x318:(0x4d797c81,0x4d42454a)}

def patch_table(original):
    data=bytearray(original);changed=[]
    for package,kind,header,size in chunks(data,struct.unpack_from('<H',data,2)[0],len(data)):
        if kind!=0x200:continue
        if U32(data,package+8)!=0x7f:continue
        for off,kind,hs,size in chunks(data,package+header,package+size):
            if kind!=0x201 or data[off+8]!=6:continue
            assert data[off+9]==0,'Unsupported color offset encoding'
            count,start=U32(data,off+12),U32(data,off+16)
            for entry,(expected,replacement) in NIGHT.items():
                if entry>=count:continue
                offset=U32(data,off+hs+entry*4)
                if offset==0xffffffff:continue
                base=off+start+offset
                entry_size,flags=struct.unpack_from('<HH',data,base)
                assert flags&1==0,'Complex outline color'
                value=base+entry_size
                if data[value+3] not in (0x1c,0x1d):continue
                color=U32(data,value+4)
                if color==expected:
                    put(data,value+4,replacement);changed.append(entry)
    assert sorted(changed)==sorted(NIGHT),f'Unsupported outline configurations: {changed}'
    assert len(original)==len(data)
    return bytes(data)
