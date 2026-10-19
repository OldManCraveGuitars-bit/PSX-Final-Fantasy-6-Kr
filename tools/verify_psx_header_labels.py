"""Execute the resident top-header literal, including its palette prefix."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
import os
PAYLOADS = ROOT / os.environ.get("FF6_QA_PAYLOADS", "work/modified")
from bytelz import decompress as unpack_tim
from korean_codec import raster
from psx_ui import old_kana
from verify_psx_ui import image,tile


def main():
    report=json.loads((ROOT/'analysis/psx-ui-insertion.json').read_text('utf8'))
    original=decompress((ROOT/'work/extracted/DEODIR/DEO.PAC').read_bytes())[0]
    overlay=decompress((PAYLOADS/'DEODIR/DEO.PAC').read_bytes())[0]
    pixels=image(unpack_tim((PAYLOADS/'DEODIR/ALLTIM.BIN').read_bytes())[0])
    occurrences=0
    for row in report['labels']:
        old=old_kana(row['source'])+b'\0';positions=[];start=0
        while (at:=original.find(old,start))>=0:positions.append(at);start=at+len(old)
        assert positions==row['occurrences'],('Missed duplicate PSX literal',row['source'])
        assert all(p+len(old)<=0x1154 for p in positions),'A label patch touches executable code'
        assert old not in overlay,('Japanese literal survived',row['source'])
        occurrences+=len(positions)
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:])
    u.mem_write(0xc8000,overlay);u.mem_write(0x36c20,(ROOT/'work/psx-name-runtime.bin').read_bytes())
    u.mem_write(0xebd40,struct.pack('<I',0x801c0000));u.mem_write(0xebd3c,struct.pack('<I',0x801d0000));u.mem_write(0xe8d10,struct.pack('<I',0x801e0000))
    cases=[]
    # This second copy, preceded by %p, was outside the former text-pool scan.
    assert original[0x10ec:0x10f4]==b'%p%K\xb5\xcf\xb9\0'
    for db in [0,1]:
        u.mem_write(0x1c0000,bytes(0x100));u.mem_write(0x1e0000,bytes(512));u.mem_write(0x1d0038,struct.pack('<I',db))
        u.reg_write(UC_MIPS_REG_A0,0x800c90ec);u.reg_write(UC_MIPS_REG_RA,0x801fffc0);u.reg_write(UC_MIPS_REG_SP,0x801ff000)
        u.emu_start(0x800cc01c,0x801fffc0,count=10000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0,hex(u.reg_read(UC_MIPS_REG_PC))
        count=struct.unpack('<H',u.mem_read(0x1c0002,2))[0];assert count==2,count
        for i,char in enumerate('부록'):
            x,y=bytes(u.mem_read(0x1e0000+i*92+36+db*20,2))
            actual=tile(pixels,x,y,8,8);im=raster(char,small=True)
            expected=bytes(bool(im.getpixel((gx,gy))) for gy in range(8) for gx in range(8))
            assert bytes(p==3 for p in actual)==expected,(db,char,x,y)
            cases.append(dict(buffer=db,char=char,UV=[x,y],Galmuri7_pixels_exact=True))
    result=dict(all_registered_literal_occurrences=occurrences,all_original_duplicates_replaced=True,
        header='부록',native_header_cases=cases,original_palette_prefix_retained=overlay[0x10ec:0x10ee]==b'%p')
    (ROOT/'analysis/psx-header-labels-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(dict(occurrences=occurrences,header='부록',native_header_glyph_cases=len(cases)))


if __name__=='__main__':main()
