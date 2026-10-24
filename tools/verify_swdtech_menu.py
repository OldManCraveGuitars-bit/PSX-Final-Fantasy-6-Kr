"""Exercise all three native saved-name glyph callers and compare glyph pixels."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn.mips_const import *
from textcodec import ROOT
from pac import decompress
from korean_codec import font_index,original_fixed,raster

def main():
    folder=ROOT/'work/v087-cache-payloads'
    menu=(folder/'HAR/MENUMENU.BIN').read_bytes()
    overlay=decompress((folder/'HAR/HARATA.PAC').read_bytes())[0]
    old_overlay=decompress((ROOT/'work/v086-cache-payloads/HAR/HARATA.PAC').read_bytes())[0]
    original=(ROOT/'work/extracted/HAR/MENUMENU.BIN').read_bytes()
    rows=json.loads((ROOT/'translations/swdtech-characters.ko.json').read_text('utf8'))
    mapping=json.loads((ROOT/'analysis/menu-big-text-insertion.json').read_text('utf8'))['mapping']
    report=json.loads((ROOT/'analysis/v087-swdtech-menu-insertion.json').read_text('utf8'))
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN)
    u.mem_map(0,0x200000);u.mem_map(0x1f800000,0x1000)
    u.mem_write(0xc8000,overlay);u.mem_write(0x140000,menu)
    u.mem_write(0x6c168,struct.pack('<I',0x1f8003c8))
    captured=[]
    def glyph(uc,at,size,user):
        base=struct.unpack('<H',uc.mem_read(0x2e0eb,2))[0]
        index=struct.unpack('<H',uc.mem_read(0x1f8003c8,2))[0]
        width=uc.mem_read(0x2e0b6,1)[0]
        captured.append((base+index*22,width,bytes(uc.mem_read(0x152fdb+base+index*22,22))))
        uc.reg_write(UC_MIPS_REG_PC,uc.reg_read(UC_MIPS_REG_RA))
    u.hook_add(UC_HOOK_CODE,glyph,begin=0x8011b048,end=0x8011b048)
    fixed=original_fixed();count=0
    for hook in report['hooks']:
        addr=hook['address'];cell=hook['symbol'].endswith('cell')
        # Delay slots and all generic callers stay intact.
        off=addr-0x800c8000
        assert overlay[off+4:off+8]==old_overlay[off+4:off+8]
        for c in range(256):
            char=rows.get(str(c),{'translation':' '})['translation']
            u.mem_write(0x1f8003c8,struct.pack('<H',c))
            u.reg_write(UC_MIPS_REG_V0,c);u.reg_write(UC_MIPS_REG_V1,0x1f8003c8)
            u.reg_write(UC_MIPS_REG_SP,0x801ff000);captured.clear()
            u.emu_start(addr,addr+8,count=1000)
            assert u.reg_read(UC_MIPS_REG_PC)==addr+8
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            if c==255 and not cell:assert not captured
            else:
                index=font_index(bytes.fromhex(mapping[char]))
                if char in fixed:
                    at=0x12fdb+font_index(fixed[char])*22;pixels=original[at:at+22]
                else:
                    im=raster(char)
                    pixels=b''.join(struct.pack('<H',sum(1<<(11-x) for x in range(12) if im.getpixel((x,y)))) for y in range(11))
                width=12 if cell or not(c==239 or c>=248) else 6
                assert captured==[(index*22,width,pixels)],(hex(addr),c,char,captured)
            count+=1
    for addr in [0x800e4ba8,0x8011adc0,0x8011b784]:
        at=addr-0x800c8000;assert overlay[at:at+8]==old_overlay[at:at+8]
    result={'native_caller_character_cases':count,'editable_characters':249,'reserved_bytes':7,
        'glyph_pixels_match':True,'original_generic_callers_preserved':True,'stack_and_continuations':True,
        'finished_name_halfspace':6,'editing_cursor_cell':12,'font_cell':[12,11]}
    (ROOT/'analysis/v087-swdtech-menu-verification.json').write_text(json.dumps(result,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
