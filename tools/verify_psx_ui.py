"""Check native PSX UI spacing and preservation of original English artwork."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
import os
PAYLOADS = ROOT / os.environ.get("FF6_QA_PAYLOADS", "work/modified")
from bytelz import decompress as byte_decompress

def image(data):
    p=8+struct.unpack_from('<I',data,8)[0];n=struct.unpack_from('<I',data,p)[0]
    return bytes(c for b in data[p+12:p+n] for c in (b&15,b>>4))

def tile(data,x,y,w,h):return b''.join(data[(y+row)*752+x:(y+row)*752+x+w] for row in range(h))

def main():
    original=byte_decompress((ROOT/'work/extracted/DEODIR/ALLTIM.BIN').read_bytes())[0]
    modified=byte_decompress((PAYLOADS/'DEODIR/ALLTIM.BIN').read_bytes())[0]
    a,b=image(original),image(modified)
    for glyph in range(95):assert tile(a,glyph%32*8,glyph//32*8,8,8)==tile(b,glyph%32*8,glyph//32*8,8,8)
    for glyph in [62,63,64,65,66,70,91,111,112,124,125]:
        assert tile(a,256+glyph%21*12,glyph//21*12,12,12)==tile(b,256+glyph%21*12,glyph//21*12,12,12)
    overlay=decompress((PAYLOADS/'DEODIR/DEO.PAC').read_bytes())[0]
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000);u.mem_write(0xc8000,overlay)
    u.mem_write(0x38000,(ROOT/'work/extracted/SLPM_861.98').read_bytes()[0x800:])
    def bios_copy(_u,_address,_size,_data):
        destination=u.reg_read(UC_MIPS_REG_A0);source=u.reg_read(UC_MIPS_REG_A1);size=u.reg_read(UC_MIPS_REG_A2)
        u.mem_write(destination&0x1fffffff,bytes(u.mem_read(source&0x1fffffff,size)))
        u.reg_write(UC_MIPS_REG_V0,destination);u.reg_write(UC_MIPS_REG_PC,u.reg_read(UC_MIPS_REG_RA))
    u.hook_add(UC_HOOK_CODE,bios_copy,begin=0x800543ac,end=0x800543ac)
    # Execute the whole original renderer, including blank primitive creation.
    # Only its final X advance changes; the sprite remains 12 by 12.
    u.mem_write(0xebd3c,struct.pack('<I',0x801d0000))
    u.mem_write(0x1d0038,bytes(4));u.mem_write(0xeebec,struct.pack('<h',12))
    u.mem_write(0xeebfc,struct.pack('<hh',21,256))
    for glyph,expected in [(0,46),(1,52)]:
        u.mem_write(0xeebe4,struct.pack('<HH',40,20));u.mem_write(0xeec02,bytes(2))
        u.reg_write(UC_MIPS_REG_A0,glyph);u.reg_write(UC_MIPS_REG_SP,0x801ff000)
        u.reg_write(UC_MIPS_REG_RA,0x801fffc0);u.emu_start(0x800d3108,0x801fffc0,count=1000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
        assert struct.unpack('<H',u.mem_read(0xeebe4,2))[0]==expected
        assert struct.unpack('<H',u.mem_read(0xeec02,2))[0]==1,'Blank glyph skipped native bookkeeping'
        assert struct.unpack('<HH',u.mem_read(0xebde4+40,4))==(12,12)
        assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    original_overlay=decompress((ROOT/'work/extracted/DEODIR/DEO.PAC').read_bytes())[0]
    # A Korean save-name preview leaves page 8 in recycled primitives. The
    # separate native border renderer must restore page 7, without changing
    # any other bytes that the original border renderer would produce.
    u.mem_write(0xebd40,struct.pack('<I',0x801c0000))
    u.mem_write(0xebde0,struct.pack('<I',0x80100000))
    u.mem_write(0x10d61c,struct.pack('<H',0x321))
    border_cases=0
    for db in (0,1):
        for glyph in range(33,127):
            results=[]
            for code in (original_overlay,overlay):
                u.mem_write(0xc8000,code)
                u.ctl_remove_cache(0x800c8000,0x800f8000)
                u.mem_write(0xebd40,struct.pack("<I",0x801c0000))
                u.mem_write(0xebd3c,struct.pack("<I",0x801d0000))
                u.mem_write(0xebde0,struct.pack("<I",0x80100000))
                u.mem_write(0x1c0000,bytes(256))
                u.mem_write(0x1d0038,struct.pack('<I',db))
                packet=bytearray(92)
                for at in (4,16):struct.pack_into('<I',packet,at,0xe1000608)
                u.mem_write(0x1e0000,bytes(packet))
                u.mem_write(0x1ff010,struct.pack('<II',3,0x801e0000))
                for reg,val in ((UC_MIPS_REG_SP,0x801ff000),(UC_MIPS_REG_RA,0x801fffc0),
                                (UC_MIPS_REG_A0,24),(UC_MIPS_REG_A1,80),
                                (UC_MIPS_REG_A2,glyph),(UC_MIPS_REG_A3,0)):
                    u.reg_write(reg,val)
                u.emu_start(0x800ce0d0,0x801fffc0,count=1000)
                assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
                results.append(bytes(u.mem_read(0x1e0000,92)))
            expected=bytearray(results[0])
            for at in (4,16):struct.pack_into('<I',expected,at,0xe1000607)
            assert results[1]==expected,('Border packet changed',db,glyph)
            border_cases+=1
    assert overlay[0x635c:0x6364]==original_overlay[0x635c:0x6364]
    address=0x800ce35c
    cases=0
    for char in [32,65,0xa1,0xdf]:
        for loop in [0,1]:
            u.mem_write(0x1e0000,bytes((char,)));u.reg_write(UC_MIPS_REG_S0,0x801e0001)
            u.reg_write(UC_MIPS_REG_S2,100);u.reg_write(UC_MIPS_REG_V0,loop)
            u.reg_write(UC_MIPS_REG_T0,0x12345678)
            stop=0x800ce310 if loop else 0x800ce364
            u.emu_start(address,stop,count=30)
            assert u.reg_read(UC_MIPS_REG_PC)==stop
            assert u.reg_read(UC_MIPS_REG_S2)==108,'Window blank cells must retain their original eight-pixel grid'
            assert u.reg_read(UC_MIPS_REG_T0)==0x12345678,'Small-space loop clobbered caller scratch state'
            cases+=1
    card=(ROOT/'work/kr-v024-card-after-write.mcr').read_bytes()
    start=card.index(b'KRN1');cache=card[start:start+3088]
    registers=[UC_MIPS_REG_T0,UC_MIPS_REG_T1,UC_MIPS_REG_T2,UC_MIPS_REG_T3,UC_MIPS_REG_T4,UC_MIPS_REG_T5]
    for valid in [True,False]:
        payload=bytearray(card[0x2200:0x4000])
        if not valid:payload[0x1100:0x1100+3088]=bytes(3088)
        u.mem_write(0x1a0000,bytes(payload))
        u.mem_write(0x30700,b'\x55'*3088);u.mem_write(0x36000,b'\xaa'*3088)
        u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_S2,0x2000)
        u.reg_write(UC_MIPS_REG_A0,0x80032400);u.reg_write(UC_MIPS_REG_A1,0x801a0000);u.reg_write(UC_MIPS_REG_A2,0x200)
        u.emu_start(0x800d928c,0x800d9294,count=50000)
        assert u.reg_read(UC_MIPS_REG_PC)==0x800d9294
        assert bytes(u.mem_read(0x32400,0x1e00))==payload
        assert bytes(u.mem_read(0x36000,3088))==(cache if valid else b'\xaa'*3088)
        assert bytes(u.mem_read(0x30700,3088))==(cache if valid else b'\x55'*3088)
        assert u.reg_read(UC_MIPS_REG_S2)==0x2000 and u.reg_read(UC_MIPS_REG_SP)==0x801ff000
    u.mem_write(0x32400,card[0x2200:0x4000]+bytes(512));u.mem_write(0x36000,bytes(3088))
    u.mem_write(0x1ff018,struct.pack('<I',0x801fffc0));u.reg_write(UC_MIPS_REG_SP,0x801ff000)
    u.emu_start(0x800d5428,0x801fffc0,count=50000)
    assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
    assert bytes(u.mem_read(0x36000,3088))==cache
    assert bytes(u.mem_read(0x30700,3088))==cache
    data={'psx_message_space_pixels':6,'psx_small_space_pixels':4,'window_tile_grid_pixels':8,'window_loop_cases':cases,
        'original_English_glyphs_preserved':106,'message_count':74,'runtime_verification':'native MIPS spacing hooks passed; screen verification separately'}
    data['physical_card_name_restore_cases']=2
    data['recycled_preview_border_cases']=border_cases
    (ROOT/'analysis/psx-ui-verification.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n','utf8')
    print(data)

if __name__=='__main__':main()
