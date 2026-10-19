"""Resolve real PSX printf UVs back to the authored Galmuri7 pixels."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
import os
PAYLOADS = ROOT / os.environ.get("FF6_QA_PAYLOADS", "work/modified")
from bytelz import decompress as byte_decompress
from korean_codec import raster
from verify_psx_ui import image,tile


def main():
    report=json.loads((ROOT/'analysis/psx-ui-insertion.json').read_text('utf8'))
    overlay=decompress((PAYLOADS/'DEODIR/DEO.PAC').read_bytes())[0]
    pixels=image(byte_decompress((PAYLOADS/'DEODIR/ALLTIM.BIN').read_bytes())[0])
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0xc8000,overlay);u.mem_write(0x36c20,(ROOT/'work/psx-name-runtime.bin').read_bytes())
    u.mem_write(0xebd40,struct.pack('<I',0x801c0000))
    u.mem_write(0xebd3c,struct.pack('<I',0x801d0000))
    u.mem_write(0xe8d10,struct.pack('<I',0x801e0000))
    cases=0
    for db in [0,1]:
        for bank,encoding in enumerate(report['small_encodings']):
            baseline=None
            for char,code in encoding.items():
                assert code not in (0xde,0xdf),('Combining kana code assigned',char,code)
                u.mem_write(0x1c0000,bytes(0x100));u.mem_write(0x1e0000,bytes(512))
                u.mem_write(0x1d0038,struct.pack('<I',db))
                u.mem_write(0x1f0000,(b'%K' if bank else b'%k')+bytes((code,0)))
                u.reg_write(UC_MIPS_REG_A0,0x801f0000)
                u.reg_write(UC_MIPS_REG_RA,0x801fffc0);u.reg_write(UC_MIPS_REG_SP,0x801ff000)
                u.emu_start(0x800cc01c,0x801fffc0,count=10000)
                assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
                assert struct.unpack('<H',u.mem_read(0x1c0002,2))[0]==1
                position=bytes(u.mem_read(0x1e0000+32+db*20,4))
                if baseline is None:baseline=position
                assert position==baseline,('Glyph baseline/advance moved',char,code,position.hex(),baseline.hex())
                x,y=bytes(u.mem_read(0x1e0000+36+db*20,2))
                actual=tile(pixels,x,y,8,8);im=raster(char,small=True)
                expected=bytes(bool(im.getpixel((gx,gy))) for gy in range(8) for gx in range(8))
                assert bytes(p==3 for p in actual)==expected,(char,bank,code,x,y)
                cases+=1
    result={'native_printf_to_Galmuri7_pixel_cases':cases,'font_banks':2,'GPU_buffers':2,
            'preview_job_labels':18,'secondary_bank_native_offset':32}
    (ROOT/'analysis/psx-font-banks-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)


if __name__=='__main__':main()
