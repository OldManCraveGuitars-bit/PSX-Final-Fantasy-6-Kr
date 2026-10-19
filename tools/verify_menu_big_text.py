"""Execute the inserted MIPS decoder for every relocated menu string."""
import json,struct
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN
from unicorn.mips_const import *
from textcodec import ROOT
from korean_codec import font_index,original_fixed,raster
from pac import decompress

def main():
    menu=(ROOT/'work/modified/HAR/MENUMENU.BIN').read_bytes()
    overlay=decompress((ROOT/'work/modified/HAR/HARATA.PAC').read_bytes())[0]
    report=json.loads((ROOT/'analysis/menu-big-text-insertion.json').read_text('utf8'))
    for char,raw in report['mapping'].items():
        if char in original_fixed():continue
        index=font_index(bytes.fromhex(raw));glyph=raster(char)
        expected=b''.join(struct.pack('<H',sum(1<<(11-x) for x in range(12) if glyph.getpixel((x,y)))) for y in range(11))
        assert menu[0x12fdb+index*22:0x12fdb+(index+1)*22]==expected
        assert menu[0x12adb+index+32]==12
    assert menu[0x12adb+0xff]==6
    u=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);u.mem_map(0,0x200000)
    u.mem_write(0x140000,menu);u.mem_write(0xc8000,overlay)
    u.mem_write(0x6c168,struct.pack('<I',0x801ee000));u.mem_write(0x6c19c,struct.pack('<I',0x801ee004))
    decoded=0
    for row in report['encoded']:
        identifier=row['id'];raw=bytes.fromhex(row['big_hex'])
        if raw==b'\0':continue
        u.mem_write(0x27ec9,bytes((0x18,identifier%255+1,identifier//255+1,0))+bytes(252))
        position=0
        while position<len(raw)-1:
            code=raw[position]
            if code==1:position+=1;continue
            u.mem_write(0x1ee000,struct.pack('<HHH',0x18 if position==0 else code,0,position))
            u.reg_write(UC_MIPS_REG_SP,0x801ff000);u.reg_write(UC_MIPS_REG_RA,0x801fffc0)
            u.emu_start(0x8011aeb8,0x801fffc0,count=3000)
            assert u.reg_read(UC_MIPS_REG_PC)==0x801fffc0
            consumed=2 if 0x1c<=code<=0x1f else 1
            original=raw[position:position+consumed];index=font_index(original)
            a,_,x=struct.unpack('<HHH',u.mem_read(0x1ee000,6))
            base=struct.unpack('<H',u.mem_read(0x2e0eb,2))[0]
            assert a*22+base==index*22,(identifier,position,original.hex(),a,base,index)
            assert x==position+consumed-1
            assert u.mem_read(0x2e0b6,1)[0]==menu[0x12adb+index+32]
            assert bytes(u.mem_read(0x27ec9,len(raw)))==raw,(identifier,position,raw.hex(),bytes(u.mem_read(0x27ec9,len(raw))).hex())
            assert u.reg_read(UC_MIPS_REG_SP)==0x801ff000
            position+=consumed;decoded+=1
    result={'native_MIPS_strings':len(report['encoded']),'native_decoded_glyphs':decoded,
        'description_and_fixed_name_reference_expansion':'passed','font':'Galmuri9','large_cell':[12,11],'space_pixels':6,
        'physical_gameplay_verification':'pending'}
    (ROOT/'analysis/native-menu-big-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n','utf8')
    print(result)
if __name__=='__main__':main()
